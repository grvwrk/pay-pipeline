import uuid
from typing import List, Optional
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

class DeterministicPolicyEngine:
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
        self.approved_tokens: set = set()

    def update_config(self, new_config: GuardrailConfig):
        self.config = new_config

    def verify_approval_token(self, token: str) -> bool:
        return token in self.approved_tokens

    def register_human_approval(self, token: str):
        self.approved_tokens.add(token)

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

        # Rule 1: Idempotency Check
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

        # Rule 3: Merchant Whitelist
        if merchant_id not in self.config.merchant_whitelist:
            rule_evaluations.append(PolicyRuleEvaluation(
                rule_name="merchant_whitelist",
                passed=False,
                description=f"Merchant {merchant_id} not whitelisted.",
                threshold_value=self.config.merchant_whitelist,
                actual_value=merchant_id
            ))
            return PolicyEvaluationResult(
                allowed=False,
                decision_code=DecisionCode.DENIED_UNAUTHORIZED_MERCHANT,
                reason=f"Merchant '{merchant_id}' is not authorized.",
                requires_human_approval=False,
                rule_evaluations=rule_evaluations,
                bounded_amount=amount,
                max_allowed_amount=self.config.max_transaction_amount_inr
            )

        # Rule 4: Hard Single-Transaction Spend Limit
        if amount > self.config.max_transaction_amount_inr:
            rule_evaluations.append(PolicyRuleEvaluation(
                rule_name="max_transaction_amount_limit",
                passed=False,
                description=f"Order amount ₹{amount:,.2f} exceeds spend limit ₹{self.config.max_transaction_amount_inr:,.2f}.",
                threshold_value=self.config.max_transaction_amount_inr,
                actual_value=amount
            ))
            return PolicyEvaluationResult(
                allowed=False,
                decision_code=DecisionCode.DENIED_SPEND_LIMIT,
                reason=f"Order total ₹{amount:,.2f} exceeds spend limit of ₹{self.config.max_transaction_amount_inr:,.2f}.",
                requires_human_approval=False,
                rule_evaluations=rule_evaluations,
                bounded_amount=amount,
                max_allowed_amount=self.config.max_transaction_amount_inr
            )
        rule_evaluations.append(PolicyRuleEvaluation(
            rule_name="max_transaction_amount_limit",
            passed=True,
            description=f"Amount ₹{amount:,.2f} within limit ₹{self.config.max_transaction_amount_inr:,.2f}.",
            threshold_value=self.config.max_transaction_amount_inr,
            actual_value=amount
        ))

        # Rule 5: Cumulative Spend Limit
        current_cum = spend_limiter.get_user_cumulative_spend(user_id)
        if current_cum + amount > self.config.max_cumulative_spend_inr:
            rule_evaluations.append(PolicyRuleEvaluation(
                rule_name="cumulative_spend_limit",
                passed=False,
                description=f"Cumulative spend ₹{current_cum + amount:,.2f} exceeds ceiling ₹{self.config.max_cumulative_spend_inr:,.2f}.",
                threshold_value=self.config.max_cumulative_spend_inr,
                actual_value=current_cum + amount
            ))
            return PolicyEvaluationResult(
                allowed=False,
                decision_code=DecisionCode.DENIED_CUMULATIVE_LIMIT,
                reason=f"Session cumulative spend would reach ₹{current_cum + amount:,.2f}, exceeding max limit ₹{self.config.max_cumulative_spend_inr:,.2f}.",
                requires_human_approval=False,
                rule_evaluations=rule_evaluations,
                bounded_amount=amount,
                max_allowed_amount=self.config.max_transaction_amount_inr
            )

        # Rule 6: Gated Approval Threshold
        if amount > self.config.approval_threshold_inr:
            if provided_approval_token and self.verify_approval_token(provided_approval_token):
                rule_evaluations.append(PolicyRuleEvaluation(
                    rule_name="gated_human_approval",
                    passed=True,
                    description=f"Order ₹{amount:,.2f} approved with valid token.",
                    threshold_value=self.config.approval_threshold_inr,
                    actual_value=amount
                ))
            else:
                token = f"appr_tok_{uuid.uuid4().hex[:12]}"
                rule_evaluations.append(PolicyRuleEvaluation(
                    rule_name="gated_human_approval",
                    passed=False,
                    description=f"Order ₹{amount:,.2f} > threshold ₹{self.config.approval_threshold_inr:,.2f}. Human confirmation required.",
                    threshold_value=self.config.approval_threshold_inr,
                    actual_value=amount
                ))
                return PolicyEvaluationResult(
                    allowed=False,
                    decision_code=DecisionCode.GATED_APPROVAL_REQUIRED,
                    reason=f"Transaction total ₹{amount:,.2f} exceeds autonomous threshold ₹{self.config.approval_threshold_inr:,.2f}. Human approval required.",
                    requires_human_approval=True,
                    approval_token=token,
                    rule_evaluations=rule_evaluations,
                    bounded_amount=amount,
                    max_allowed_amount=self.config.max_transaction_amount_inr
                )

        return PolicyEvaluationResult(
            allowed=True,
            decision_code=DecisionCode.APPROVED,
            reason=f"All safety checks passed. Transaction bounded and authorized.",
            requires_human_approval=False,
            rule_evaluations=rule_evaluations,
            bounded_amount=amount,
            max_allowed_amount=self.config.max_transaction_amount_inr
        )

policy_engine = DeterministicPolicyEngine()
