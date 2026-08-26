from typing import Optional, Dict, Any
from backend.app.models.cart import Cart
from backend.app.config import settings
from backend.app.models.order import RazorpayOrder, PaymentCaptureResult, RefundResult
from backend.app.guardrails.policy_engine import policy_engine
from backend.app.guardrails.idempotency import idempotency_manager
from backend.app.guardrails.spend_limiter import spend_limiter
from backend.app.payment.razorpay_client import razorpay_client
from backend.app.audit.audit_service import audit_service

class PrivilegedMoneyTools:
    @classmethod
    def create_order_guarded(
        cls,
        cart: Cart,
        user_id: str = "user_default_buyer",
        idempotency_key: Optional[str] = None,
        approval_token: Optional[str] = None
    ) -> Dict[str, Any]:
        policy_res = policy_engine.evaluate(
            cart=cart,
            user_id=user_id,
            idempotency_key=idempotency_key,
            provided_approval_token=approval_token
        )

        if not policy_res.allowed:
            audit_service.record_event(
                actor_id=user_id,
                actor_role="CHECKOUT_AGENT",
                action="CREATE_ORDER_DENIED",
                arguments={"cart_id": cart.cart_id, "amount": cart.total_amount, "decision_code": policy_res.decision_code},
                guardrail_decision=policy_res.decision_code.value,
                approval_required=policy_res.requires_human_approval,
                result_status="DENIED",
                explainability_notes=f"Guardrail denial: {policy_res.reason}"
            )
            return {
                "success": False,
                "decision_code": policy_res.decision_code,
                "reason": policy_res.reason,
                "requires_approval": policy_res.requires_human_approval,
                "approval_token": policy_res.approval_token,
                "policy_evaluation": policy_res.model_dump()
            }

        order = razorpay_client.create_order(
            amount_inr=cart.total_amount,
            cart_id=cart.cart_id,
            idempotency_key=idempotency_key,
            notes={"user_id": user_id, "items_count": str(len(cart.items))}
        )

        if idempotency_key:
            idempotency_manager.register_key(idempotency_key, order.model_dump())

        audit_service.record_event(
            actor_id=user_id,
            actor_role="CHECKOUT_AGENT",
            action="CREATE_RAZORPAY_ORDER",
            tool_name="create_order",
            arguments={"order_id": order.order_id, "amount": order.amount, "currency": order.currency, "idempotency_key": idempotency_key},
            guardrail_decision="APPROVED",
            result_status="SUCCESS",
            explainability_notes=f"Order {order.order_id} created on Razorpay test rails for ₹{order.amount:,.2f}."
        )

        return {
            "success": True,
            "order": order.model_dump(),
            "policy_evaluation": policy_res.model_dump()
        }

    @classmethod
    def capture_payment_guarded(
        cls,
        order_id: str,
        amount_inr: float,
        user_id: str = "user_default_buyer",
        method: str = "upi",
        force_fail: bool = False
    ) -> Dict[str, Any]:
        res = razorpay_client.simulate_payment_capture(order_id, amount_inr, method, force_fail)
        
        if res.status == "captured":
            audit_service.record_event(
                actor_id=user_id,
                actor_role="RAZORPAY_API",
                action="PAYMENT_CAPTURE_AWAITING_WEBHOOK",
                tool_name="capture_payment",
                arguments={"payment_id": res.payment_id, "order_id": order_id, "amount": amount_inr, "method": method},
                guardrail_decision="APPROVED",
                result_status="PENDING",
                explainability_notes=(f"Payment {res.payment_id} was initiated in {settings.PAYMENT_PROVIDER_MODE} mode. "
                                      "It is not marked successful until a signed payment.captured webhook is received.")
            )
            return {"success": False, "verification_pending": True, "payment": res.model_dump()}
        else:
            audit_service.record_event(
                actor_id=user_id,
                actor_role="RAZORPAY_API",
                action="CAPTURE_PAYMENT_FAILED",
                tool_name="capture_payment",
                arguments={"payment_id": res.payment_id, "order_id": order_id, "error": res.error_code},
                guardrail_decision="FAILED",
                result_status="FAILED",
                explainability_notes=f"Payment attempt for order {order_id} failed: {res.error_description}"
            )
            return {"success": False, "payment": res.model_dump(), "error": res.error_description}

    @classmethod
    def issue_refund_guarded(
        cls,
        payment_id: str,
        amount_inr: float,
        user_id: str = "user_default_buyer",
        reason: str = "Customer request"
    ) -> Dict[str, Any]:
        try:
            refund = razorpay_client.process_refund(payment_id, amount_inr, reason)
            audit_service.record_event(
                actor_id=user_id,
                actor_role="CHECKOUT_AGENT",
                action="ISSUE_REFUND_SUCCESS",
                tool_name="issue_refund",
                arguments={"refund_id": refund.refund_id, "payment_id": payment_id, "amount": amount_inr, "reason": reason},
                guardrail_decision="APPROVED",
                result_status="SUCCESS",
                explainability_notes=f"Refund {refund.refund_id} processed for ₹{amount_inr:,.2f}."
            )
            return {"success": True, "refund": refund.model_dump()}
        except Exception as e:
            audit_service.record_event(
                actor_id=user_id,
                actor_role="CHECKOUT_AGENT",
                action="ISSUE_REFUND_DENIED",
                tool_name="issue_refund",
                arguments={"payment_id": payment_id, "amount": amount_inr, "error": str(e)},
                guardrail_decision="DENIED",
                result_status="DENIED",
                explainability_notes=f"Refund denied: {str(e)}"
            )
            return {"success": False, "error": str(e)}

money_tools = PrivilegedMoneyTools()
