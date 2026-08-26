import json
from typing import Dict, Any, Tuple
from backend.app.payment.razorpay_client import razorpay_client
from backend.app.payment.state_machine import state_machine
from backend.app.models.order import TransactionState
from backend.app.audit.audit_service import audit_service
from backend.app.guardrails.spend_limiter import spend_limiter
from backend.app.database.repositories import order_repo, cart_repo, product_repo


class AuthoritativeWebhookHandler:
    """
    Authoritative Webhook Receiver.
    Validates HMAC-SHA256 signature, transitions order/payment states,
    decrements inventory atomically, and records verified audit events.
    """

    @classmethod
    def handle_webhook(cls, raw_payload: str, signature: str) -> Tuple[bool, str, Dict[str, Any]]:
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

        payload = json.loads(raw_payload)
        event_type = payload.get("event", "unknown")
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = entity.get("order_id", "unknown_order")
        payment_id = entity.get("id", "unknown_pay")
        amount = float(entity.get("amount", 0)) / 100.0

        if event_type == "payment.captured":
            buyer_id = razorpay_client.reconcile_verified_payment(order_id, payment_id, amount)
            if buyer_id:
                spend_limiter.record_spend(buyer_id, amount)

            # Atomically decrement inventory for the order's cart items
            order = order_repo.get_order(order_id)
            if order and order.cart_id:
                cart = cart_repo.get_cart(order.cart_id)
                if cart:
                    for item in cart.items:
                        product_repo.decrement_inventory(item.product_id, item.quantity)

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

        elif event_type == "payment.failed":
            order_repo.update_order_state(order_id, "failed", TransactionState.PAYMENT_FAILED)
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

        return True, f"EVENT_ACKNOWLEDGED_{event_type}", {}


webhook_handler = AuthoritativeWebhookHandler()
