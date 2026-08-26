import json
from typing import Dict, Any, Tuple
from backend.app.payment.razorpay_client import razorpay_client
from backend.app.payment.state_machine import state_machine
from backend.app.models.order import TransactionState
from backend.app.audit.audit_service import audit_service

class AuthoritativeWebhookHandler:
    @classmethod
    def handle_webhook(cls, raw_payload: str, signature: str) -> Tuple[bool, str, Dict[str, Any]]:
        is_valid = razorpay_client.verify_webhook_signature(raw_payload, signature)
        if not is_valid:
            audit_service.record_event(
                actor_id="WEBHOOK_RECEIVER",
                actor_role="RAZORPAY_WEBHOOK",
                action="WEBHOOK_SIGNATURE_REJECTED",
                arguments={"signature": signature},
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
            audit_service.record_event(
                actor_id="RAZORPAY_SERVER",
                actor_role="PAYMENT_GATEWAY",
                action="PAYMENT_CAPTURED_EVENT",
                arguments={"order_id": order_id, "payment_id": payment_id, "amount": amount, "event": event_type},
                transaction_state=TransactionState.PAYMENT_CAPTURED,
                result_status="SUCCESS",
                explainability_notes=f"Authoritative webhook verified for {payment_id}. State transitioned to PAYMENT_CAPTURED."
            )
            return True, "PAYMENT_CAPTURED_VERIFIED", {"order_id": order_id, "payment_id": payment_id, "amount": amount}

        elif event_type == "payment.failed":
            audit_service.record_event(
                actor_id="RAZORPAY_SERVER",
                actor_role="PAYMENT_GATEWAY",
                action="PAYMENT_FAILED_EVENT",
                arguments={"order_id": order_id, "payment_id": payment_id, "amount": amount, "event": event_type},
                transaction_state=TransactionState.PAYMENT_FAILED,
                result_status="FAILED",
                explainability_notes=f"Authoritative payment failure event for {payment_id} verified. No money captured."
            )
            return True, "PAYMENT_FAILED_VERIFIED", {"order_id": order_id, "payment_id": payment_id, "amount": amount}

        return True, f"EVENT_ACKNOWLEDGED_{event_type}", {}

webhook_handler = AuthoritativeWebhookHandler()
