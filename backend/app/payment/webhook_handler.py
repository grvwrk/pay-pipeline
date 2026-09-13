import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.database.db import SessionLocal
from backend.app.payment.razorpay_client import razorpay_client
from backend.app.models.order import LOCAL_ORDER_NOTE_KEY, PaymentCaptureResult, RazorpayOrder, TransactionState
from backend.app.payment.state_machine import state_machine
from backend.app.audit.audit_service import audit_service
from backend.app.database.repositories import order_repo, cart_repo, product_repo, spend_repo, payment_repo

logger = logging.getLogger(__name__)

# A payment link mints its own Razorpay order when it is paid, so a capture event
# arrives referencing that order rather than the one this system created. Both
# families are handled, and the local order is resolved by reference/notes first.
CAPTURE_EVENTS = {"payment.captured", "order.paid", "payment_link.paid"}
FAILURE_EVENTS = {"payment.failed", "payment_link.cancelled", "payment_link.expired"}

TERMINAL_CAPTURED_STATES = (TransactionState.COMPLETED, TransactionState.PAYMENT_CAPTURED)


class AuthoritativeWebhookHandler:
    """
    Authoritative server-side processor for Razorpay payment webhooks.
    Guarantees transactional integrity by executing balance updates,
    inventory decrementing, and state transitions inside an explicit Unit-of-Work session.
    """

    # ------------------------------------------------------------------ parsing

    @staticmethod
    def _entity(payload_data: Dict[str, Any], key: str) -> Dict[str, Any]:
        wrapper = payload_data.get(key) or {}
        entity = wrapper.get("entity") or {}
        return entity if isinstance(entity, dict) else {}

    @classmethod
    def parse_event(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten a Razorpay event into the fields this system needs, collecting every
        candidate that could identify the local order, most trustworthy first.
        """
        payload_data = payload.get("payload") or {}
        payment = cls._entity(payload_data, "payment")
        link = cls._entity(payload_data, "payment_link")
        remote_order = cls._entity(payload_data, "order")

        def note(entity: Dict[str, Any]) -> Optional[str]:
            notes = entity.get("notes")
            return notes.get(LOCAL_ORDER_NOTE_KEY) if isinstance(notes, dict) else None

        # reference_id and notes carry OUR order id; order_id fields carry Razorpay's.
        candidates: List[Optional[str]] = [
            link.get("reference_id"),
            note(link),
            note(payment),
            note(remote_order),
            payment.get("order_id"),
            remote_order.get("id"),
        ]
        seen, order_id_candidates = set(), []
        for candidate in candidates:
            if candidate and candidate not in seen:
                seen.add(candidate)
                order_id_candidates.append(candidate)

        # Paise -> INR, preferring the amount actually moved.
        raw_amount = (
            payment.get("amount")
            if payment.get("amount") is not None
            else link.get("amount_paid") or link.get("amount") or remote_order.get("amount") or 0
        )
        try:
            amount = float(raw_amount) / 100.0
        except (TypeError, ValueError):
            amount = 0.0

        return {
            "event_type": payload.get("event", "unknown"),
            "order_id_candidates": order_id_candidates,
            "payment_link_id": link.get("id"),
            "payment_id": payment.get("id") or "unknown_pay",
            "amount": amount,
            "error_description": payment.get("error_description"),
        }

    @staticmethod
    def resolve_order(
        candidates: List[str],
        payment_link_id: Optional[str],
        db: Session
    ) -> Optional[RazorpayOrder]:
        """First candidate that names a known local order; else match on a stored link id."""
        for candidate in candidates:
            order = order_repo.get_order(candidate, db=db)
            if order:
                return order

        if payment_link_id:
            order = order_repo.find_by_note("payment_link_id", payment_link_id, db=db)
            if order:
                return order

        # Razorpay does not always echo notes back, so fall back to the link's own
        # order id if reconciliation has previously recorded it against an order.
        for candidate in candidates:
            order = order_repo.find_by_note("link_order_id", candidate, db=db)
            if order:
                return order
        return None

    # ------------------------------------------------------- state application

    @classmethod
    def apply_capture(
        cls,
        order: RazorpayOrder,
        payment_id: str,
        amount_inr: float,
        db: Session
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Move a verified capture into local state: order transition, payment record,
        cumulative spend, inventory. Caller owns the session and its commit.
        """
        if abs(amount_inr - order.amount) > 0.01:
            logger.error(
                "Capture amount mismatch for order %s: expected %f, got %f",
                order.order_id, order.amount, amount_inr
            )
            return False, "PAYMENT_AMOUNT_MISMATCH", {"expected": order.amount, "received": amount_inr}

        if order.state in TERMINAL_CAPTURED_STATES:
            logger.info("Order %s already captured (state: %s). Acknowledging idempotently.", order.order_id, order.state)
            return True, "EVENT_ALREADY_PROCESSED", {"order_id": order.order_id, "payment_id": payment_id}

        buyer_id = razorpay_client.reconcile_verified_payment(
            order_id=order.order_id,
            payment_id=payment_id,
            amount_inr=amount_inr,
            db=db
        )

        if buyer_id:
            spend_repo.record_spend(buyer_id, amount_inr, db=db)

        if order.cart_id:
            cart = cart_repo.get_cart(order.cart_id, db=db)
            if cart:
                for item in cart.items:
                    ok = product_repo.decrement_inventory(
                        product_id=item.product_id,
                        quantity=item.quantity,
                        db=db
                    )
                    if not ok:
                        raise ValueError(f"Insufficient stock to fulfill product {item.product_id}")

        return True, "PAYMENT_CAPTURED_VERIFIED", {
            "order_id": order.order_id,
            "payment_id": payment_id,
            "amount": amount_inr,
        }

    @classmethod
    def apply_failure(
        cls,
        order: RazorpayOrder,
        payment_id: str,
        amount_inr: float,
        db: Session,
        error_description: Optional[str] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Record an authoritative failed attempt. A captured order is never walked back."""
        if order.state in TERMINAL_CAPTURED_STATES or order.state == TransactionState.REFUNDED:
            logger.info(
                "Ignoring failure event for order %s already in state %s.", order.order_id, order.state
            )
            return True, "EVENT_IGNORED_ORDER_SETTLED", {"order_id": order.order_id, "state": order.state.value}

        if not state_machine.can_transition(order.state, TransactionState.PAYMENT_FAILED):
            return True, "EVENT_IGNORED_ILLEGAL_TRANSITION", {"order_id": order.order_id, "state": order.state.value}

        order_repo.update_order_state(
            order_id=order.order_id,
            status="failed",
            state=TransactionState.PAYMENT_FAILED,
            db=db
        )

        # Persist the attempt so the failure is visible alongside the order.
        if payment_id and payment_id != "unknown_pay" and not payment_repo.get_payment(payment_id, db=db):
            user_id = (order.notes or {}).get("user_id") or "user_default_buyer"
            payment_repo.record_payment(
                PaymentCaptureResult(
                    payment_id=payment_id,
                    order_id=order.order_id,
                    amount=amount_inr or order.amount,
                    currency=order.currency or "INR",
                    status="failed",
                    method="webhook",
                    webhook_verified=True,
                    error_description=error_description or "Payment attempt failed at the gateway."
                ),
                user_id=user_id,
                db=db
            )

        return True, "PAYMENT_FAILED_VERIFIED", {
            "order_id": order.order_id,
            "payment_id": payment_id,
            "amount": amount_inr,
        }

    # ------------------------------------------------------------- entry point

    @classmethod
    def handle_webhook(
        cls,
        raw_payload: str,
        signature: str,
        db: Optional[Session] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Verifies the incoming Razorpay webhook signature and processes state transitions.
        If a db session is passed, it uses it; otherwise it manages its own atomic SessionLocal transaction block.
        """
        # 1. Signature Verification
        if not razorpay_client.verify_webhook_signature(raw_payload, signature):
            audit_service.record_event(
                actor_id="WEBHOOK_RECEIVER",
                actor_role="RAZORPAY_WEBHOOK",
                action="WEBHOOK_SIGNATURE_REJECTED",
                arguments={"signature": signature},
                guardrail_decision="REJECTED_SIGNATURE_MISMATCH",
                result_status="DENIED",
                explainability_notes="Authoritative webhook signature mismatch. Request rejected."
            )
            return False, "INVALID_WEBHOOK_SIGNATURE", {}

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as err:
            logger.error("Failed to parse webhook JSON payload: %s", err)
            return False, "MALFORMED_JSON_PAYLOAD", {}

        event = cls.parse_event(payload)
        event_type = event["event_type"]

        if event_type not in CAPTURE_EVENTS and event_type not in FAILURE_EVENTS:
            return True, f"EVENT_ACKNOWLEDGED_{event_type.upper()}", {}

        is_capture = event_type in CAPTURE_EVENTS
        session = db or SessionLocal()
        try:
            order = cls.resolve_order(event["order_id_candidates"], event["payment_link_id"], session)
            if not order:
                logger.error(
                    "Webhook %s could not be matched to a local order. Candidates: %s, link: %s",
                    event_type, event["order_id_candidates"], event["payment_link_id"]
                )
                audit_service.record_event(
                    actor_id="RAZORPAY_SERVER",
                    actor_role="RAZORPAY_WEBHOOK",
                    action="WEBHOOK_ORDER_UNRESOLVED",
                    arguments={
                        "event": event_type,
                        "candidates": event["order_id_candidates"],
                        "payment_link_id": event["payment_link_id"],
                    },
                    result_status="FAILED",
                    explainability_notes="Signature was valid but no local order matched the event."
                )
                if not db:
                    session.close()
                return False, "ORDER_NOT_FOUND", {"candidates": event["order_id_candidates"]}

            if is_capture:
                ok, code, data = cls.apply_capture(order, event["payment_id"], event["amount"], session)
            else:
                ok, code, data = cls.apply_failure(
                    order, event["payment_id"], event["amount"], session, event["error_description"]
                )

            if not ok:
                if not db:
                    session.rollback()
                    session.close()
                return False, code, data

            if not db:
                session.commit()

        except Exception as exc:
            if not db:
                session.rollback()
                session.close()
            logger.error("Webhook processing transaction failed for %s: %s", event_type, exc)
            audit_service.record_event(
                actor_id="RAZORPAY_SERVER",
                actor_role="PAYMENT_GATEWAY",
                action="PAYMENT_CAPTURE_TRANSACTION_FAILED",
                arguments={"event": event_type, "payment_id": event["payment_id"], "error": str(exc)},
                result_status="FAILED",
                explainability_notes=f"Atomic webhook transaction failed and was rolled back: {exc}"
            )
            if db:
                raise exc
            return False, "TRANSACTION_PROCESSING_ERROR", {"error": str(exc)}
        finally:
            if not db:
                try:
                    session.close()
                except Exception:
                    pass

        if is_capture:
            audit_service.record_event(
                actor_id="RAZORPAY_SERVER",
                actor_role="PAYMENT_GATEWAY",
                action="PAYMENT_CAPTURED_EVENT",
                arguments={**data, "event": event_type},
                transaction_state=TransactionState.PAYMENT_CAPTURED.value,
                result_status="SUCCESS",
                explainability_notes=(
                    f"Authoritative webhook verified for {event['payment_id']}. "
                    f"Order {data.get('order_id')} transitioned to COMPLETED."
                )
            )
        else:
            audit_service.record_event(
                actor_id="RAZORPAY_SERVER",
                actor_role="PAYMENT_GATEWAY",
                action="PAYMENT_FAILED_EVENT",
                arguments={**data, "event": event_type},
                transaction_state=TransactionState.PAYMENT_FAILED.value,
                result_status="FAILED",
                explainability_notes=(
                    f"Authoritative failure event ({event_type}) verified for {event['payment_id']}. "
                    "No money captured."
                )
            )

        return True, code, data


# Singleton instance
webhook_handler = AuthoritativeWebhookHandler()
