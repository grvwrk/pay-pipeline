from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import datetime

class DecisionCode(str, Enum):
    APPROVED = "APPROVED"
    DENIED_SPEND_LIMIT = "DENIED_SPEND_LIMIT"
    DENIED_CUMULATIVE_LIMIT = "DENIED_CUMULATIVE_LIMIT"
    DENIED_CUMULATIVE_SPEND_EXCEEDED = "DENIED_CUMULATIVE_SPEND_EXCEEDED"
    DENIED_OUT_OF_STOCK = "DENIED_OUT_OF_STOCK"
    DENIED_UNAUTHORIZED_CATEGORY = "DENIED_UNAUTHORIZED_CATEGORY"
    DENIED_UNAUTHORIZED_MERCHANT = "DENIED_UNAUTHORIZED_MERCHANT"
    DENIED_CURRENCY_MISMATCH = "DENIED_CURRENCY_MISMATCH"
    DENIED_QUANTITY_EXCEEDED = "DENIED_QUANTITY_EXCEEDED"
    DENIED_IDEMPOTENCY_COLLISION = "DENIED_IDEMPOTENCY_COLLISION"
    GATED_APPROVAL_REQUIRED = "GATED_APPROVAL_REQUIRED"

class PolicyRuleEvaluation(BaseModel):
    rule_name: str
    passed: bool
    description: str
    threshold_value: Any = None
    actual_value: Any = None

class PolicyEvaluationResult(BaseModel):
    allowed: bool
    decision_code: DecisionCode
    reason: str
    requires_human_approval: bool = False
    approval_token: Optional[str] = None
    rule_evaluations: List[PolicyRuleEvaluation] = Field(default_factory=list)
    evaluated_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    bounded_amount: float
    max_allowed_amount: float

class GuardrailConfig(BaseModel):
    max_transaction_amount_inr: float = 5000.0
    max_cumulative_spend_inr: float = 15000.0
    approval_threshold_inr: float = 3000.0
    max_item_quantity: int = 5
    allowed_currency: str = "INR"
    allowed_categories: List[str] = Field(default_factory=lambda: [
        "smartphones",
        "mobile_accessories",
        "mechanical_keyboards",
        "computer_peripherals",
        "workspace_accessories",
        "developer_gear",
        "ergonomics",
        "audio_equipment",
        "nutrition_and_fitness",
        "running_shoes",
        "health_and_groceries"
    ])
    merchant_whitelist: List[str] = Field(default_factory=lambda: ["merch_pay_pipeline_01"])