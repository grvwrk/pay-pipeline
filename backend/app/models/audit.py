from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
import datetime


class ActorRole(str, Enum):
    USER = "USER"
    INTENT_ROUTER = "INTENT_ROUTER"
    CATALOG_AGENT = "CATALOG_AGENT"
    UPSELL_AGENT = "UPSELL_AGENT"
    CHECKOUT_AGENT = "CHECKOUT_AGENT"
    GUARDRAIL_ENGINE = "GUARDRAIL_ENGINE"
    RAZORPAY_API = "RAZORPAY_API"
    WEBHOOK_RECEIVER = "WEBHOOK_RECEIVER"
    EXTERNAL_AI_BUYER = "EXTERNAL_AI_BUYER"
    AUDIT_ENGINE = "AUDIT_ENGINE"
    TOOL_DISPATCHER = "TOOL_DISPATCHER"
    SYSTEM = "SYSTEM"
    PAYMENT_GATEWAY = "PAYMENT_GATEWAY"
    RAZORPAY_WEBHOOK = "RAZORPAY_WEBHOOK"


class AuditRecord(BaseModel):
    index: int
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    event_id: str
    prev_hash: str
    record_hash: str
    actor_id: str
    actor_role: ActorRole
    action: str
    intent: Optional[str] = None
    tool_name: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    guardrail_decision: Optional[str] = None
    approval_required: bool = False
    transaction_state: Optional[str] = None
    result_status: str  # SUCCESS, DENIED, FAILED, PENDING
    signature: str  # HMAC-SHA256 signature
    explainability_notes: str = ""
    latency_ms: float = 0.0


class AuditChainVerificationResult(BaseModel):
    is_valid: bool
    total_records: int
    genesis_hash: str = "0000000000000000000000000000000000000000000000000000000000000000"
    latest_hash: str = ""
    tampered_index: Optional[int] = None
    error_detail: Optional[str] = None
    verified_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class ExplainabilityReport(BaseModel):
    order_id: str
    final_status: str
    guardrail_decision: str
    policy_reason: str
    timeline: List[Dict[str, Any]] = Field(default_factory=list)