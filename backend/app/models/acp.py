from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ACPProductSummary(BaseModel):
    sku: str
    name: str
    category: str
    price_inr: float
    stock_status: str
    spec_summary: Dict[str, Any]
    direct_checkout_supported: bool = True

class ACPDiscoveryResponse(BaseModel):
    protocol_version: str = "ACP/1.0"
    merchant_id: str
    merchant_name: str
    currency: str = "INR"
    catalog: List[ACPProductSummary]
    spend_limit_inr: float
    direct_order_supported: bool = True
    mcp_tools_url: str

class ACPQuoteRequest(BaseModel):
    skus: List[str]
    quantities: List[int] = Field(default_factory=lambda: [1])
    include_upsell_bundles: bool = True
    agent_id: str = "ai_buyer_agent_ext"

class ACPQuoteResponse(BaseModel):
    quote_id: str
    skus: List[str]
    subtotal: float
    bundle_discount: float
    total_amount: float
    currency: str = "INR"
    guardrail_precheck: str # "PASS" or "DENIED"
    expires_in_seconds: int = 300
    expires_at: str

class ACPCheckoutRequest(BaseModel):
    quote_id: str
    idempotency_key: str
    buyer_agent_id: str
    delivery_instructions: str = "Digital/Express Dispatch"

class ACPCheckoutResponse(BaseModel):
    status: str # "ORDER_CREATED" or "DENIED"
    order_id: Optional[str] = None
    amount: float
    currency: str = "INR"
    razorpay_payment_link: Optional[str] = None
    audit_event_id: str
    signature: str
    message: str
