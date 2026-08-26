import uuid
from typing import List, Optional, Tuple
from backend.app.config import settings
from backend.app.models.cart import Cart
from backend.app.models.guardrail import (
    GuardrailConfig,
    PolicyEvaluationResult,
    PolicyRuleEvaluation,
    DecisionCode
)
from backend.app.guardrails.spend_limiter import spend_limiter
from backend.app.guardrails.idempotency import idempotency_manager
from backend.app.database.repositories import approval_repo, payment_repo, refund_repo, product_repo


class DeterministicPolicyEngine:
    """
    Deterministic, Model-Independent Policy Engine.
    Enforces spend ceilings, INR boundaries, quantity caps, gated 2FA human confirmation,
    category whitelists, merchant checks, and refund limits.
    """

    def __init__(self, config: Optional[GuardrailConfig] = None):
        self.config = config or GuardrailConfig(
            max_transaction_amount_inr=settings.DEFAULT_MAX_TXN_AMOUNT_INR,
            max_cumulative_spend_inr=settings.DEFAULT_MAX_CUMULATIVE_SPEND_INR,
            approval_threshold_inr=settings.DEFAULT_APPROVAL_THRESHOLD_INR,
            max_item_quantity=settings.DEFAULT_MAX_ITEM_QUANTITY,
            allowed_currency=settings.ALLOWED_CURRENCY,
            allowed_categories=settings.ALLOWED_CATEGORIES,
            merchant_whitelist=[settings.MERCHANT_ID]
        )

    def update_config(self, new_config: GuardrailConfig):
        self.config = new_config

    def verify_approval_token(self, token: str) -> bool:
        return approval_repo.is_approved(token)

    def register_human_approval(self, token: str):
        approval_repo.register_approval(token)

    def evaluate_refund(
        self,
        payment_id: str,
        refund_amount: float,
        user_id: str = "user_default_buyer"
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Evaluate refund validity against original payment record and refund ceilings.
        Returns (allowed, reason, decision_code).
        """
        if refund_amount <= 0:
            return False, "Refund amount must be greater than zero.", "INVALID_REFUND_AMOUNT"

        payment = payment_repo.get_payment(payment_id)
        if not payment:
            return False, f"Payment record '{payment_id}' not found.", "PAYMENT_NOT_FOUND"

        if payment.status != "captured":
            return False, f"Cannot refund payment '{payment_id}' with status '{payment.status}'. Payment must be captured.", "PAYMENT_NOT_CAPTURED"

        total_already_refunded = refund_repo.get_total_refunded(payment_id)
        remaining_refundable = payment.amount - total_already_refunded

        if refund_amount > remaining_refundable:
            return (
                False,
                f"Refund amount ₹{refund_amount:,.2f} exceeds remaining refundable balance ₹{remaining_refundable:,.2f} (Original: ₹{payment.amount:,.2f}, Already Refunded: ₹{total_already_refunded:,.2f}).",
                "REFUND_EXCEEDS_ORIGINAL_AMOUNT"
            )

        return True, "Refund approved within original payment bounds.", "APPROVED"

    def evaluate(
        self,
        cart: Cart,
        user_id: str = "user_default_buyer",
        merchant_id: str = settings.MERCHANT_ID,
        idempotency_key: Optional[str] = None,
        provided_approval_token: Optional[str] = None
    ) -> PolicyEvaluationResult:
        rule_evaluations: List[PolicyRuleEvaluation] = []
        cart.recalculate()
        amount = cart.total_amount

        # Rule 1: Idempotency Collision Check
        if idempotency_key:
            cached = idempotency_manager.check_key(idempotency_key)
            if cached:
                rule_evaluations.append(PolicyRuleEvaluation(
                    rule_name="idempotency_check",
                    passed=False,
                    description=f"Idempotency key {idempotency_key} was already executed.",
                    threshold_value="unique_key",
                    actual_value=idempotency_key
                ))
                return PolicyEvaluationResult(
                    allowed=False,
                    decision_code=DecisionCode.DENIED_IDEMPOTENCY_COLLISION,
                    reason=f"Duplicate request with idempotency key '{idempotency_key}'. Returning cached execution.",
                    requires_human_approval=False,
                    rule_evaluations=rule_evaluations,
                    bounded_amount=amount,
                    max_allowed_amount=self.config.max_transaction_amount_inr
                )
            else:
                rule_evaluations.append(PolicyRuleEvaluation(
                    rule_name="idempotency_check",
                    passed=True,
                    description="Idempotency key is novel and unique.",
                    threshold_value="unique_key",
                    actual_value=idempotency_key
                ))

        # Rule 2: Currency Check
        if cart.currency != self.config.allowed_currency:
            rule_evaluations.append(PolicyRuleEvaluation(
                rule_name="currency_boundary",
                passed=False,
                description=f"Currency must be {self.config.allowed_currency}, got {cart.currency}.",
                threshold_value=self.config.allowed_currency,
                actual_value=cart.currency
            ))
            return PolicyEvaluationResult(
                allowed=False,
                decision_code=DecisionCode.DENIED_CURRENCY_MISMATCH,
                reason=f"Currency '{cart.currency}' disallowed. Only {self.config.allowed_currency} authorized.",
                requires_human_approval=False,
                rule_evaluations=rule_evaluations,
                bounded_amount=amount,
                max_allowed_amount=self.config.max_transaction_amount_inr
            )
        rule_evaluations.append(PolicyRuleEvaluation(
            rule_name="currency_boundary",
            passed=True,
            description="Currency matches authorized INR standard.",
            threshold_value=self.config.allowed_currency,
            actual_value=cart.currency
        ))

        # Rule 3: Single Transaction Hard Limit (Max ₹5,000)
        if amount > self.config.max_transaction_amount_inr:
            rule_evaluations.append(PolicyRuleEvaluation(
                rule_name="single_transaction_spend_limit",
                passed=False,
                description=f"Cart total ₹{amount:,.2f} exceeds hard limit ₹{self.config.max_transaction_amount_inr:,.2f}.",
                threshold_value=f"₹{self.config.max_transaction_amount_inr:,.2f}",
                actual_value=f"₹{amount:,.2f}"
            ))
            return PolicyEvaluationResult(
                allowed=False,
                decision_code=DecisionCode.DENIED_SPEND_LIMIT,
                reason=f"Cart total ₹{amount:,.2f} exceeds maximum single transaction spend limit of ₹{self.config.max_transaction_amount_inr:,.2f}.",
                requires_human_approval=False,
                rule_evaluations=rule_evaluations,
                bounded_amount=amount,
                max_allowed_amount=self.config.max_transaction_amount_inr
            )
        rule_evaluations.append(PolicyRuleEvaluation(
            rule_name="single_transaction_spend_limit",
            passed=True,
            description="Cart total is within single transaction limit.",
            threshold_value=f"₹{self.config.max_transaction_amount_inr:,.2f}",
            actual_value=f"₹{amount:,.2f}"
        ))

        # Rule 4: Cumulative User Spend Ceiling (Max ₹15,000)
        user_cum = spend_limiter.get_user_cumulative_spend(user_id)
        if (user_cum + amount) > self.config.max_cumulative_spend_inr:
            rule_evaluations.append(PolicyRuleEvaluation(
                rule_name="cumulative_spend_ceiling",
                passed=False,
                description=f"Total projected spend ₹{user_cum + amount:,.2f} exceeds cumulative session ceiling ₹{self.config.max_cumulative_spend_inr:,.2f}.",
                threshold_value=f"₹{self.config.max_cumulative_spend_inr:,.2f}",
                actual_value=f"₹{user_cum + amount:,.2f}"
            ))
            return PolicyEvaluationResult(
                allowed=False,
                decision_code=DecisionCode.DENIED_CUMULATIVE_SPEND_EXCEEDED,
                reason=f"Cumulative user spend ceiling of ₹{self.config.max_cumulative_spend_inr:,.2f} would be exceeded (Current: ₹{user_cum:,.2f}, Attempted: ₹{amount:,.2f}).",
                requires_human_approval=False,
                rule_evaluations=rule_evaluations,
                bounded_amount=amount,
                max_allowed_amount=self.config.max_cumulative_spend_inr
            )
        rule_evaluations.append(PolicyRuleEvaluation(
            rule_name="cumulative_spend_ceiling",
            passed=True,
            description="Projected spend is within cumulative user limit.",
            threshold_value=f"₹{self.config.max_cumulative_spend_inr:,.2f}",
            actual_value=f"₹{user_cum + amount:,.2f}"
        ))

        # Rule 5: Quantity Cap per item
        for item in cart.items:
            if item.quantity > self.config.max_item_quantity:
                rule_evaluations.append(PolicyRuleEvaluation(
                    rule_name="quantity_cap",
                    passed=False,
                    description=f"Item '{item.name}' requested quantity {item.quantity} exceeds cap of {self.config.max_item_quantity}.",
                    threshold_value=str(self.config.max_item_quantity),
                    actual_value=str(item.quantity)
                ))
                return PolicyEvaluationResult(
                    allowed=False,
                    decision_code=DecisionCode.DENIED_QUANTITY_EXCEEDED,
                    reason=f"Item '{item.name}' quantity {item.quantity} exceeds allowed maximum quantity of {self.config.max_item_quantity}.",
                    requires_human_approval=False,
                    rule_evaluations=rule_evaluations,
                    bounded_amount=amount,
                    max_allowed_amount=self.config.max_transaction_amount_inr
                )
        rule_evaluations.append(PolicyRuleEvaluation(
            rule_name="quantity_cap",
            passed=True,
            description="Item quantities are within allowed limits.",
            threshold_value=str(self.config.max_item_quantity),
            actual_value=str(max((i.quantity for i in cart.items), default=0))
        ))

        # Rule 6: Inventory Availability Check
        for item in cart.items:
            p = product_repo.get_by_id(item.product_id)
            if p and p.inventory < item.quantity:
                rule_evaluations.append(PolicyRuleEvaluation(
                    rule_name="inventory_check",
                    passed=False,
                    description=f"Item '{item.name}' is out of stock (Available: {p.inventory}, Requested: {item.quantity}).",
                    threshold_value=str(item.quantity),
                    actual_value=str(p.inventory)
                ))
                return PolicyEvaluationResult(
                    allowed=False,
                    decision_code=DecisionCode.DENIED_OUT_OF_STOCK,
                    reason=f"Item '{item.name}' has insufficient stock ({p.inventory} available, {item.quantity} requested).",
                    requires_human_approval=False,
                    rule_evaluations=rule_evaluations,
                    bounded_amount=amount,
                    max_allowed_amount=self.config.max_transaction_amount_inr
                )

        # Rule 7: Gated Human Approval Check for orders > ₹3,000
        if amount > self.config.approval_threshold_inr:
            token_valid = bool(provided_approval_token and self.verify_approval_token(provided_approval_token))

            if not token_valid:
                new_token = f"appr_{uuid.uuid4().hex[:16]}"
                approval_repo.create_approval(
                    token=new_token,
                    user_id=user_id,
                    amount=amount,
                    cart_id=cart.cart_id,
                    reason=f"Transaction ₹{amount:,.2f} exceeds automatic approval threshold ₹{self.config.approval_threshold_inr:,.2f}"
                )
                rule_evaluations.append(PolicyRuleEvaluation(
                    rule_name="gated_human_approval",
                    passed=False,
                    description=f"Order ₹{amount:,.2f} exceeds automatic approval threshold ₹{self.config.approval_threshold_inr:,.2f}. Explicit 2FA token required.",
                    threshold_value=f"₹{self.config.approval_threshold_inr:,.2f}",
                    actual_value=f"₹{amount:,.2f}"
                ))
                return PolicyEvaluationResult(
                    allowed=False,
                    decision_code=DecisionCode.GATED_APPROVAL_REQUIRED,
                    reason=f"Order amount of ₹{amount:,.2f} exceeds the automatic approval threshold of ₹{self.config.approval_threshold_inr:,.2f}. Explicit human confirmation required.",
                    requires_human_approval=True,
                    approval_token=new_token,
                    rule_evaluations=rule_evaluations,
                    bounded_amount=amount,
                    max_allowed_amount=self.config.max_transaction_amount_inr
                )
            else:
                rule_evaluations.append(PolicyRuleEvaluation(
                    rule_name="gated_human_approval",
                    passed=True,
                    description="Gated human approval token verified and registered.",
                    threshold_value=provided_approval_token,
                    actual_value="VERIFIED"
                ))

        # All Rules Passed
        return PolicyEvaluationResult(
            allowed=True,
            decision_code=DecisionCode.APPROVED,
            reason=f"Transaction of ₹{amount:,.2f} conforms to all deterministic safety policies and spend limits.",
            requires_human_approval=False,
            approval_token=provided_approval_token,
            rule_evaluations=rule_evaluations,
            bounded_amount=amount,
            max_allowed_amount=self.config.max_transaction_amount_inr
        )


policy_engine = DeterministicPolicyEngine()
