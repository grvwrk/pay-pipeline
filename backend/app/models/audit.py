from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import datetime

class AuditRecord(BaseModel):
    index: int
    timestamp: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    event_id: str
    prev_hash: str
    record_hash: str
    actor_id: str
    actor_role: str # USER, INTENT_ROUTER, CATALOG_AGENT, UPSELL_AGENT, CHECKOUT_AGENT, GUARDRAIL_ENGINE, RAZORPAY_API, WEBHOOK_RECEIVER, EXTERNAL_AI_BUYER
    action: str
    intent: Optional[str] = None
    tool_name: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    guardrail_decision: Optional[str] = None
    approval_required: bool = False
    transaction_state: Optional[str] = None
    result_status: str # SUCCESS, DENIED, FAILED, PENDING
    signature: str # HMAC-SHA256 signature
    explainability_notes: str = ""

class AuditChainVerificationResult(BaseModel):
    is_valid: bool
    total_records: int
    genesis_hash: str
    latest_hash: str
    tampered_index: Optional[int] = None
    error_detail: Optional[str] = None
    verified_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")

class ExplainabilityReport(BaseModel):
    event_id: str
    timestamp: str
    user_intent: str
    selected_items: List[Dict[str, Any]]
    agent_reasoning: str
    upsell_contribution: Dict[str, Any]
    guardrail_check_summary: Dict[str, Any]
    money_action_proof: Dict[str, Any]
    cryptographic_hash: str
    signature: str
