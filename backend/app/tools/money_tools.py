from typing import Optional, Dict, Any
from backend.app.models.cart import Cart
from backend.app.config import settings
from backend.app.guardrails.policy_engine import policy_engine
from backend.app.guardrails.idempotency import idempotency_manager
from backend.app.payment.razorpay_client import razorpay_client
from backend.app.audit.audit_service import audit_service
from backend.app.tools.dispatcher import tool_dispatcher, ToolRiskLevel
from backend.app.database.repositories import payment_repo, order_repo, cart_repo


class PrivilegedMoneyTools:
    """
    Privileged Money-Moving Tools (Class B - High Risk).
    Every execution must pass through deterministic policy evaluation 
    and record to the cryptographic audit ledger.
    """

    @classmethod
    def create_order_guarded(
        cls,
        cart: Cart,
        user_id: str,
        idempotency_key: Optional[str] = None,
        approval_token: Optional[str] = None
    ) -> Dict[str, Any]:
        if not user_id:
            raise ValueError("user_id is required for financial operations.")

        policy_res = policy_engine.evaluate(
            cart=cart,
            user_id=user_id,
            idempotency_key=idempotency_key,
            provided_approval_token=approval_token
        )

        if not policy_res.allowed:
            decision_val = policy_res.decision_code.value if hasattr(policy_res.decision_code, 'value') else str(policy_res.decision_code)
            audit_service.record_event(
                actor_id=user_id,
                actor_role="CHECKOUT_AGENT",
                action="CREATE_ORDER_DENIED",
                arguments={"cart_id": cart.cart_id, "amount": cart.total_amount, "decision_code": decision_val},
                guardrail_decision=decision_val,
                approval_required=policy_res.requires_human_approval,
                result_status="DENIED",
                explainability_notes=f"Guardrail denial: {policy_res.reason}"
            )
            return {
                "success": False,
                "decision_code": decision_val,
                "reason": policy_res.reason,
                "requires_approval": policy_res.requires_human_approval,
                "approval_token": policy_res.approval_token,
                "policy_evaluation": policy_res.model_dump()
            }

        cart_repo.save_cart(cart)

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
        user_id: str,
        method: str = "upi",
        force_fail: bool = False
    ) -> Dict[str, Any]:
        if not user_id:
            raise ValueError("user_id is required for financial operations.")

        order = order_repo.get_order(order_id)
        if not order:
            err = f"Order {order_id} not found."
            audit_service.record_event(
                actor_id=user_id,
                actor_role="CHECKOUT_AGENT",
                action="CAPTURE_PAYMENT_FAILED",
                tool_name="capture_payment",
                arguments={"order_id": order_id, "error": err},
                guardrail_decision="DENIED",
                result_status="FAILED",
                explainability_notes=err
            )
            return {"success": False, "error": err}

        if amount_inr != order.amount:
            err = f"Payment amount ₹{amount_inr:,.2f} does not match authorized order amount ₹{order.amount:,.2f}."
            audit_service.record_event(
                actor_id=user_id,
                actor_role="CHECKOUT_AGENT",
                action="PAYMENT_AMOUNT_MISMATCH",
                tool_name="capture_payment",
                arguments={"order_id": order_id, "attempted_amount": amount_inr, "expected_amount": order.amount},
                guardrail_decision="DENIED",
                result_status="FAILED",
                explainability_notes=err
            )
            return {"success": False, "error": err}

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
        user_id: str,
        reason: str = "Customer request"
    ) -> Dict[str, Any]:
        if not user_id:
            raise ValueError("user_id is required for financial operations.")

        allowed, policy_reason, decision_code = policy_engine.evaluate_refund(
            payment_id=payment_id,
            refund_amount=amount_inr,
            user_id=user_id
        )

        decision_val = decision_code.value if hasattr(decision_code, 'value') else str(decision_code)

        if not allowed:
            audit_service.record_event(
                actor_id=user_id,
                actor_role="CHECKOUT_AGENT",
                action="ISSUE_REFUND_DENIED",
                tool_name="issue_refund",
                arguments={"payment_id": payment_id, "amount": amount_inr, "reason": reason, "decision_code": decision_val},
                guardrail_decision="DENIED",
                result_status="DENIED",
                explainability_notes=f"Refund denied: {policy_reason}"
            )
            return {
                "success": False,
                "decision_code": decision_val,
                "error": policy_reason
            }

        try:
            refund = razorpay_client.process_refund(payment_id, amount_inr, reason, user_id=user_id)
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
                action="ISSUE_REFUND_FAILED",
                tool_name="issue_refund",
                arguments={"payment_id": payment_id, "amount": amount_inr, "error": str(e)},
                guardrail_decision="ERROR",
                result_status="FAILED",
                explainability_notes=f"Refund error: {str(e)}"
            )
            return {"success": False, "error": str(e)}

    @classmethod
    def cancel_payment(
        cls,
        payment_id: str,
        user_id: str,
        reason: str = "User cancelled"
    ) -> Dict[str, Any]:
        if not user_id:
            raise ValueError("user_id is required for payment cancellation.")

        payment = payment_repo.get_payment(payment_id)
        if not payment:
            return {"success": False, "error": f"Payment {payment_id} not found."}

        if payment.status in ["captured", "refunded"]:
            err_msg = f"Cannot cancel payment {payment_id} in final state '{payment.status}'."
            audit_service.record_event(
                actor_id=user_id,
                actor_role="CHECKOUT_AGENT",
                action="CANCEL_PAYMENT_DENIED",
                tool_name="cancel_payment",
                arguments={"payment_id": payment_id, "reason": reason},
                guardrail_decision="DENIED",
                result_status="FAILED",
                explainability_notes=err_msg
            )
            return {"success": False, "error": err_msg}

        payment_repo.update_status(payment_id, "cancelled", error_code="CANCELLED_BY_USER", error_desc=reason)
        audit_service.record_event(
            actor_id=user_id,
            actor_role="CHECKOUT_AGENT",
            action="PAYMENT_CANCELLED",
            tool_name="cancel_payment",
            arguments={"payment_id": payment_id, "reason": reason},
            guardrail_decision="APPROVED",
            result_status="CANCELLED",
            explainability_notes=f"Payment {payment_id} cancelled by user: {reason}"
        )
        return {"success": True, "message": f"Payment {payment_id} cancelled."}


money_tools = PrivilegedMoneyTools()

# Register money tools with ToolDispatcher
tool_dispatcher.register_tool("create_order", "Create guarded Razorpay test order from cart", ToolRiskLevel.HIGH, money_tools.create_order_guarded, requires_guardrail=True)
tool_dispatcher.register_tool("capture_payment", "Initiate and capture payment on Razorpay rails", ToolRiskLevel.HIGH, money_tools.capture_payment_guarded, requires_guardrail=True)
tool_dispatcher.register_tool("issue_refund", "Process refund bounded by original payment amount", ToolRiskLevel.HIGH, money_tools.issue_refund_guarded, requires_guardrail=True)
tool_dispatcher.register_tool("cancel_payment", "Cancel pending payment transaction", ToolRiskLevel.HIGH, money_tools.cancel_payment, requires_guardrail=True)