import base64
import hmac
import hashlib
import json
import uuid
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.models.order import (
    LOCAL_ORDER_NOTE_KEY, PaymentCaptureResult, RazorpayOrder, RefundResult, TransactionState
)
from backend.app.database.repositories import order_repo, payment_repo, refund_repo, spend_repo
from backend.app.payment.state_machine import state_machine

logger = logging.getLogger(__name__)


class RazorpayApiError(RuntimeError):
    """A sanitized Razorpay test-mode API error suitable for API responses."""


class RazorpayClientWrapper:
    """
    Razorpay Test Rails & Simulator Client.
    All transactions are persisted into SQLite and verifiable against signatures.
    """

    def __init__(self):
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET or settings.AUDIT_HMAC_SECRET
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

    def create_order(
        self,
        amount_inr: float,
        cart_id: str,
        idempotency_key: Optional[str] = None,
        notes: Optional[Dict[str, str]] = None,
        db: Optional[Session] = None
    ) -> RazorpayOrder:
        if amount_inr <= 0:
            raise ValueError("Order amount must be positive")
        if settings.PAYMENT_PROVIDER_MODE == "razorpay":
            return self._create_razorpay_test_order(amount_inr, cart_id, idempotency_key, notes, db=db)
        if settings.PAYMENT_PROVIDER_MODE != "simulator":
            raise RazorpayApiError("PAYMENT_PROVIDER_MODE must be 'simulator' or 'razorpay'")

        order_id = f"order_{uuid.uuid4().hex[:14]}"
        receipt = f"rcpt_{uuid.uuid4().hex[:8]}"
        amount_in_paise = int(amount_inr * 100)

        order = RazorpayOrder(
            order_id=order_id,
            cart_id=cart_id,
            amount=amount_inr,
            amount_in_paise=amount_in_paise,
            currency="INR",
            status="created",
            receipt=receipt,
            notes=notes or {},
            state=TransactionState.ORDER_CREATED,
            idempotency_key=idempotency_key
        )
        order_repo.create_order(order, db=db)
        return order

    def _create_razorpay_test_order(
        self,
        amount_inr: float,
        cart_id: str,
        idempotency_key: Optional[str],
        notes: Optional[Dict[str, str]],
        db: Optional[Session] = None
    ) -> RazorpayOrder:
        if not self.key_id or not settings.RAZORPAY_KEY_SECRET:
            raise RazorpayApiError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are required for Razorpay mode")
        receipt = f"rcpt_{cart_id[-16:]}"
        body = json.dumps({
            "amount": int(round(amount_inr * 100)),
            "currency": "INR",
            "receipt": receipt,
            "notes": {**(notes or {}), "cart_id": cart_id, "idempotency_key": idempotency_key or ""},
        }).encode("utf-8")
        credentials = base64.b64encode(f"{self.key_id}:{settings.RAZORPAY_KEY_SECRET}".encode("utf-8")).decode("ascii")
        request = Request(
            "https://api.razorpay.com/v1/orders",
            data=body,
            method="POST",
            headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/json"}
        )
        try:
            with urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise RazorpayApiError(f"Razorpay order request failed with HTTP {error.code}") from error
        except URLError as error:
            raise RazorpayApiError("Unable to reach Razorpay API") from error

        order = RazorpayOrder(
            order_id=payload["id"],
            cart_id=cart_id,
            amount=amount_inr,
            amount_in_paise=payload["amount"],
            currency=payload["currency"],
            status=payload.get("status", "created"),
            receipt=payload.get("receipt", receipt),
            notes=notes or {},
            state=TransactionState.ORDER_CREATED,
            idempotency_key=idempotency_key
        )
        order_repo.create_order(order, db=db)
        return order

    def simulate_payment_capture(
        self,
        order_id: str,
        amount_inr: float,
        method: str = "upi",
        force_fail: bool = False,
        db: Optional[Session] = None
    ) -> PaymentCaptureResult:
        if settings.PAYMENT_PROVIDER_MODE != "simulator":
            raise RazorpayApiError("Payment capture simulation is unavailable in Razorpay mode; complete Razorpay Checkout and wait for its webhook.")

        order = order_repo.get_order(order_id, db=db)
        if not order:
            raise ValueError(f"Unknown order {order_id}")
        if abs(amount_inr - order.amount) > 0.01:
            raise ValueError(f"Payment amount ({amount_inr}) must match authorized order amount ({order.amount})")

        payment_id = f"pay_{uuid.uuid4().hex[:14]}"
        user_id = order.notes.get("user_id", "user_default_buyer") if order.notes else "user_default_buyer"

        if force_fail:
            target_state = state_machine.transition(order.state, TransactionState.PAYMENT_FAILED)
            res = PaymentCaptureResult(
                payment_id=payment_id,
                order_id=order_id,
                amount=amount_inr,
                currency="INR",
                status="failed",
                method=method,
                error_code="PAYMENT_DECLINED_BY_BANK",
                error_description="Customer bank declined transaction simulation."
            )
            order_repo.update_order_state(order_id, "failed", target_state, db=db)
        else:
            target_state = state_machine.transition(order.state, TransactionState.PAYMENT_CAPTURED)
            res = PaymentCaptureResult(
                payment_id=payment_id,
                order_id=order_id,
                amount=amount_inr,
                currency="INR",
                status="captured",
                method=method
            )
            order_repo.update_order_state(order_id, "paid", target_state, db=db)

        payment_repo.record_payment(res, user_id=user_id, db=db)
        return res

    def process_refund(
        self,
        payment_id: str,
        amount_inr: float,
        reason: str = "Customer request",
        user_id: str = "user_default_buyer",
        db: Optional[Session] = None
    ) -> RefundResult:
        payment = payment_repo.get_payment(payment_id, db=db)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        if payment.status != "captured":
            raise ValueError(f"Cannot refund payment {payment_id} with status '{payment.status}'. Only captured payments can be refunded.")

        if amount_inr <= 0:
            raise ValueError("Refund amount must be positive")

        if amount_inr > payment.amount:
            raise ValueError(f"Refund amount (₹{amount_inr:,.2f}) cannot exceed original payment amount (₹{payment.amount:,.2f})")

        order = order_repo.get_order(payment.order_id, db=db)
        if order:
            target_state = state_machine.transition(order.state, TransactionState.REFUNDED)
            order_repo.update_order_state(order.order_id, "refunded", target_state, db=db)

        refund_id = f"rfnd_{uuid.uuid4().hex[:14]}"
        refund = RefundResult(
            refund_id=refund_id,
            payment_id=payment_id,
            order_id=payment.order_id,
            amount=amount_inr,
            currency="INR",
            status="processed",
            reason=reason
        )
        refund_repo.create_refund(refund, user_id=user_id, db=db)

        # Deduct refunded amount from cumulative user spend total
        spend_repo.decrement_spend(user_id, amount_inr, db=db)

        return refund

    def fetch_order(self, order_id: str, db: Optional[Session] = None) -> Optional[RazorpayOrder]:
        return order_repo.get_order(order_id, db=db)

    @staticmethod
    def _describe_api_error(status_code: int, detail: str) -> str:
        """
        Turn a Razorpay error body into one sentence a buyer-facing surface can show.

        The reason matters more than the status: a test-mode quota being exhausted and
        a bad key both surface as "no payment link", and only the text tells them apart.
        """
        code = ""
        description = ""
        try:
            error = (json.loads(detail) or {}).get("error") or {}
            code = str(error.get("code") or "")
            description = str(error.get("description") or "")
        except Exception:
            description = (detail or "").strip()[:200]

        if code == "RATE_LIMIT_EXCEEDED" or status_code == 429:
            return (
                f"Razorpay rejected the request as rate limited (HTTP {status_code})"
                + (f": {description}" if description else "")
                + ". Test-mode quotas reset on Razorpay's side; switch payment.provider_mode "
                  "to 'simulator' to keep testing offline."
            )
        if status_code in (401, 403):
            return f"Razorpay rejected the API credentials (HTTP {status_code})" + (f": {description}" if description else "") + "."
        return (
            f"Razorpay returned HTTP {status_code}"
            + (f": {description}" if description else "")
            + "."
        )

    def _api_call(
        self,
        path: str,
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None,
        timeout: int = 15
    ) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Authenticated call against the Razorpay REST API.

        Returns `(payload, reason)`: exactly one is set. The reason exists because a
        silently swallowed failure here shows up far away as a missing "Pay" button
        with nothing to explain it.
        """
        if not self.key_id or not settings.RAZORPAY_KEY_SECRET:
            logger.warning("RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET is not set. Skipping Razorpay API call %s.", path)
            return None, "Razorpay API credentials are not configured (RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET)."

        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        credentials = base64.b64encode(
            f"{self.key_id}:{settings.RAZORPAY_KEY_SECRET}".encode("utf-8")
        ).decode("ascii")
        request = Request(
            f"https://api.razorpay.com/v1{path}",
            data=body,
            method=method,
            headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/json"}
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8")), None
        except HTTPError as error:
            try:
                detail = error.read().decode("utf-8")
            except Exception:
                detail = ""
            logger.error("Razorpay %s %s failed with HTTP %s. %s", method, path, error.code, detail)
            return None, self._describe_api_error(error.code, detail)
        except URLError as error:
            logger.error("Unable to reach Razorpay for %s %s: %s", method, path, error)
            return None, f"Razorpay is unreachable: {error.reason}."
        except Exception as error:
            logger.error("Razorpay %s %s failed: %s", method, path, error)
            return None, f"Razorpay request failed: {error}."

    def _api_request(
        self,
        path: str,
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None,
        timeout: int = 15
    ) -> Optional[Dict[str, Any]]:
        """Authenticated call against the Razorpay REST API. Returns None on any failure."""
        return self._api_call(path, method=method, payload=payload, timeout=timeout)[0]

    def create_payment_link(self, order: RazorpayOrder, db: Optional[Session] = None) -> Optional[str]:
        """
        Create a hosted payment link for an order and return its short URL.

        A payment link mints its OWN Razorpay order when it is paid, so the payment
        that comes back references that link order, not the one stored locally. Both
        `reference_id` and `notes` therefore carry the local order id, and the link id
        is persisted onto the order, so webhooks and reconciliation can map back here.
        """
        return self.create_payment_link_result(order, db=db)[0]

    def create_payment_link_result(
        self,
        order: RazorpayOrder,
        db: Optional[Session] = None
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Same as `create_payment_link`, but returns `(short_url, reason)` so a caller can
        tell the buyer *why* no link exists instead of rendering nothing at all.

        A link already minted for this order is reused: test-mode payment links are a
        finite quota, and re-issuing one per retry burns it for no benefit.
        """
        existing = (order.notes or {}).get("payment_link_url")
        if existing:
            return existing, None

        # Simulator mode must stay offline. Calling the live API here mints a real
        # test-mode link against a locally-invented order id, burns the account's
        # payment_link quota, and makes "switch to simulator" fail to isolate anything.
        if settings.PAYMENT_PROVIDER_MODE != "razorpay":
            return None, (
                "Payment links require payment.provider_mode 'razorpay'; "
                f"the current mode is '{settings.PAYMENT_PROVIDER_MODE}'. "
                "Pay via the cart page's test payment instead."
            )

        payload, reason = self._api_call("/payment_links", method="POST", payload={
            "amount": int(round(order.amount * 100)),
            "currency": "INR",
            "accept_partial": False,
            "reference_id": order.order_id,
            "description": f"Payment for Order {order.order_id}",
            "customer": {
                "name": settings.PAYMENT_CUSTOMER_NAME,
                "contact": settings.PAYMENT_CUSTOMER_CONTACT,
                "email": settings.PAYMENT_CUSTOMER_EMAIL
            },
            "notify": {
                "sms": False,
                "email": False
            },
            "reminder_enable": False,
            "notes": {LOCAL_ORDER_NOTE_KEY: order.order_id},
        })
        if not payload:
            logger.error("Failed to create Razorpay payment link for Order ID '%s'. %s", order.order_id, reason or "")
            return None, reason or "Razorpay did not return a payment link."

        short_url = payload.get("short_url")
        link_id = payload.get("id")
        if link_id:
            order_repo.merge_notes(
                order.order_id,
                {"payment_link_id": link_id, "payment_link_url": short_url or ""},
                db=db
            )
        return short_url, None

    def fetch_remote_payment_link(self, link_id: str) -> Optional[Dict[str, Any]]:
        """Read a payment link's authoritative status and its payment attempts from Razorpay."""
        return self._api_request(f"/payment_links/{link_id}")

    def find_remote_payment_link_by_reference(self, reference_id: str) -> Optional[Dict[str, Any]]:
        """
        Locate a payment link by the local order id it was created against.

        Needed for orders whose link id was never stored locally; Razorpay has no
        reference_id filter on this endpoint, so the list is scanned client-side.
        """
        payload = self._api_request("/payment_links")
        links = (payload or {}).get("payment_links")
        if not isinstance(links, list):
            return None
        matches = [
            link for link in links
            if isinstance(link, dict) and link.get("reference_id") == reference_id
        ]
        if not matches:
            return None
        return max(matches, key=lambda link: link.get("created_at") or 0)

    def fetch_remote_order_payments(self, remote_order_id: str) -> list:
        """Read the payment attempts Razorpay holds against one of its order ids."""
        payload = self._api_request(f"/orders/{remote_order_id}/payments")
        items = (payload or {}).get("items")
        return items if isinstance(items, list) else []

    def fetch_payment(self, payment_id: str, db: Optional[Session] = None) -> Optional[PaymentCaptureResult]:
        return payment_repo.get_payment(payment_id, db=db)

    def fetch_refund(self, refund_id: str, db: Optional[Session] = None) -> Optional[RefundResult]:
        return refund_repo.get_refund(refund_id, db=db)

    def verify_webhook_signature(self, raw_payload: str, signature: str) -> bool:
        if not self.webhook_secret:
            return False
        expected_signature = hmac.new(
            self.webhook_secret.encode("utf-8"),
            raw_payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_signature, signature)

    def reconcile_verified_payment(
        self, 
        order_id: str, 
        payment_id: str, 
        amount_inr: float, 
        db: Optional[Session] = None
    ) -> Optional[str]:
        order = order_repo.get_order(order_id, db=db)
        if not order:
            return None

        target_state = state_machine.transition(order.state, TransactionState.COMPLETED)
        order_repo.update_order_state(order_id, "paid", target_state, db=db)
        
        user_id = order.notes.get("user_id") if order.notes else None
        user_id = user_id or "user_default_buyer"

        # Ensure payment record exists (mandatory for webhook captures in live mode)
        payment = payment_repo.get_payment(payment_id, db=db)
        if not payment:
            capture_res = PaymentCaptureResult(
                payment_id=payment_id,
                order_id=order_id,
                amount=amount_inr,
                currency=order.currency or "INR",
                status="captured",
                method="webhook",
                webhook_verified=True
            )
            payment_repo.record_payment(capture_res, user_id=user_id, db=db)
        else:
            payment_repo.update_status(payment_id, "captured", db=db)

        return user_id


razorpay_client = RazorpayClientWrapper()