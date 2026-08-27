import json
import logging
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from backend.app.database.db import SessionLocal
from backend.app.payment.razorpay_client import razorpay_client
from backend.app.models.order import TransactionState
from backend.app.audit.audit_service import audit_service
from backend.app.database.repositories import order_repo, cart_repo, product_repo, spend_repo

logger = logging.getLogger(__name__)


class AuthoritativeWebhookHandler:
    """
    Authoritative server-side processor for Razorpay payment webhooks.
    Guarantees transactional integrity by executing balance updates,
    inventory decrementing, and state transitions inside an explicit Unit-of-Work session.
    """

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
        is_valid = razorpay_client.verify_webhook_signature(raw_payload, signature)
        if not is_valid:
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

        event_type = payload.get("event", "unknown")
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id", "unknown_order")
        payment_id = payment_entity.get("id", "unknown_pay")
        amount = float(payment_entity.get("amount", 0)) / 100.0

        # 2. Process payment.captured event
        if event_type == "payment.captured":
            session = db or SessionLocal()
            try:
                order = order_repo.get_order(order_id, db=session)
                if not order:
                    if not db:
                        session.close()
                    return False, "ORDER_NOT_FOUND", {"order_id": order_id}

                # Verify payment amount matches authorized order amount
                if abs(amount - order.amount) > 0.01:
                    logger.error("Webhook amount mismatch for order %s: expected %f, got %f", order_id, order.amount, amount)
                    if not db:
                        session.close()
                    return False, "PAYMENT_AMOUNT_MISMATCH", {"expected": order.amount, "received": amount}

                # Idempotency check: Skip duplicate processing if already completed/captured
                if order.state in (TransactionState.COMPLETED, TransactionState.PAYMENT_CAPTURED):
                    logger.info("Order %s already processed (state: %s). Acknowledging webhook idempotently.", order_id, order.state)
                    if not db:
                        session.close()
                    return True, "EVENT_ALREADY_PROCESSED", {"order_id": order_id, "payment_id": payment_id}

                # Reconcile payment status and state
                buyer_id = razorpay_client.reconcile_verified_payment(
                    order_id=order_id,
                    payment_id=payment_id,
                    amount_inr=amount,
                    db=session
                )
                
                # Record spend against user cumulative spend tracker
                if buyer_id:
                    spend_repo.record_spend(buyer_id, amount, db=session)

                # Atomically decrement product inventory for cart items
                if order.cart_id:
                    cart = cart_repo.get_cart(order.cart_id, db=session)
                    if cart:
                        for item in cart.items:
                            success = product_repo.decrement_inventory(
                                product_id=item.product_id,
                                quantity=item.quantity,
                                db=session
                            )
                            if not success:
                                raise ValueError(f"Insufficient stock to fulfill product {item.product_id}")

                # Commit only if managing session locally
                if not db:
                    session.commit()

            except Exception as exc:
                if not db:
                    session.rollback()
                logger.error("Webhook processing transaction failed for order %s: %s", order_id, exc)
                audit_service.record_event(
                    actor_id="RAZORPAY_SERVER",
                    actor_role="PAYMENT_GATEWAY",
                    action="PAYMENT_CAPTURE_TRANSACTION_FAILED",
                    arguments={"order_id": order_id, "payment_id": payment_id, "error": str(exc)},
                    result_status="FAILED",
                    explainability_notes=f"Atomic webhook transaction failed and was rolled back: {exc}"
                )
                if db:
                    raise exc
                return False, "TRANSACTION_PROCESSING_ERROR", {"error": str(exc)}
            finally:
                if not db:
                    session.close()

            audit_service.record_event(
                actor_id="RAZORPAY_SERVER",
                actor_role="PAYMENT_GATEWAY",
                action="PAYMENT_CAPTURED_EVENT",
                arguments={"order_id": order_id, "payment_id": payment_id, "amount": amount, "event": event_type},
                transaction_state=TransactionState.PAYMENT_CAPTURED.value,
                result_status="SUCCESS",
                explainability_notes=f"Authoritative webhook verified for {payment_id}. Order {order_id} transitioned to COMPLETED."
            )
            return True, "PAYMENT_CAPTURED_VERIFIED", {"order_id": order_id, "payment_id": payment_id, "amount": amount}

        # 3. Process payment.failed event
        elif event_type == "payment.failed":
            session = db or SessionLocal()
            try:
                order_repo.update_order_state(
                    order_id=order_id,
                    status="failed",
                    state=TransactionState.PAYMENT_FAILED,
                    db=session
                )
                if not db:
                    session.commit()
            except Exception as exc:
                if not db:
                    session.rollback()
                if db:
                    raise exc
                return False, "TRANSACTION_PROCESSING_ERROR", {"error": str(exc)}
            finally:
                if not db:
                    session.close()

            audit_service.record_event(
                actor_id="RAZORPAY_SERVER",
                actor_role="PAYMENT_GATEWAY",
                action="PAYMENT_FAILED_EVENT",
                arguments={"order_id": order_id, "payment_id": payment_id, "amount": amount, "event": event_type},
                transaction_state=TransactionState.PAYMENT_FAILED.value,
                result_status="FAILED",
                explainability_notes=f"Authoritative payment failure event for {payment_id} verified. No money captured."
            )
            return True, "PAYMENT_FAILED_VERIFIED", {"order_id": order_id, "payment_id": payment_id, "amount": amount}

        return True, f"EVENT_ACKNOWLEDGED_{event_type.upper()}", {}


# Singleton instance
webhook_handler = AuthoritativeWebhookHandler()