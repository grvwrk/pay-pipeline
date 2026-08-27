import base64
import hmac
import hashlib
import json
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.models.order import RazorpayOrder, PaymentCaptureResult, RefundResult, TransactionState
from backend.app.database.repositories import order_repo, payment_repo, refund_repo, spend_repo


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
        if amount_inr != order.amount:
            raise ValueError("Payment amount must exactly match the authorized order amount")

        payment_id = f"pay_{uuid.uuid4().hex[:14]}"
        user_id = order.notes.get("user_id", "user_default_buyer") if order.notes else "user_default_buyer"

        if force_fail:
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
            order_repo.update_order_state(order_id, "failed", TransactionState.PAYMENT_FAILED, db=db)
        else:
            res = PaymentCaptureResult(
                payment_id=payment_id,
                order_id=order_id,
                amount=amount_inr,
                currency="INR",
                status="captured",
                method=method
            )
            order_repo.update_order_state(order_id, "paid", TransactionState.PAYMENT_PENDING, db=db)

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

        order = order_repo.get_order(payment.order_id, db=db)
        if order:
            order_repo.update_order_state(order.order_id, "refunded", TransactionState.REFUNDED, db=db)

        return refund

    def fetch_order(self, order_id: str, db: Optional[Session] = None) -> Optional[RazorpayOrder]:
        return order_repo.get_order(order_id, db=db)

    def fetch_payment(self, payment_id: str, db: Optional[Session] = None) -> Optional[PaymentCaptureResult]:
        return payment_repo.get_payment(payment_id, db=db)

    def fetch_refund(self, refund_id: str, db: Optional[Session] = None) -> Optional[RefundResult]:
        return refund_repo.get_refund(refund_id, db=db)

    def verify_webhook_signature(self, raw_payload: str, signature: str) -> bool:
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

        order_repo.update_order_state(order_id, "paid", TransactionState.COMPLETED, db=db)
        payment_repo.update_status(payment_id, "captured", db=db)
        return order.notes.get("user_id") if order.notes else None


razorpay_client = RazorpayClientWrapper()