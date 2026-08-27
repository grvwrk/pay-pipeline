from typing import Any, Dict, List, Optional
from pydantic import Field
from llama_index.core.workflow import Event
from backend.app.models.catalog import Product
from backend.app.models.cart import BundleOffer, Cart


class IntentClassifiedEvent(Event):
    intent: str
    user_query: str
    user_id: str = "user_default_buyer"
    target_sku: Optional[str] = None
    target_category: Optional[str] = None
    max_price: Optional[float] = None
    include_bundle: bool = False
    approval_token: Optional[str] = None
    idempotency_key: Optional[str] = None
    force_fail_payment: bool = False
    order_id: Optional[str] = None
    payment_id: Optional[str] = None
    refund_amount: Optional[float] = None


class CatalogSearchEvent(Event):
    query: Optional[str] = None
    category: Optional[str] = None
    max_price: Optional[float] = None
    user_id: str = "user_default_buyer"
    intent: str = "PRODUCT_SEARCH"


class CatalogResultEvent(Event):
    products: List[Product]
    top_choice: Optional[Product] = None
    upsell_bundle: Optional[BundleOffer] = None
    user_query: str = ""
    user_id: str = "user_default_buyer"
    agent_summary: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    provider: str = "deterministic"


class CheckoutEvent(Event):
    user_id: str = "user_default_buyer"
    target_sku: Optional[str] = None
    query: str = ""
    max_price: Optional[float] = None
    include_bundle: bool = False
    approval_token: Optional[str] = None
    idempotency_key: Optional[str] = None
    force_fail_payment: bool = False


class CheckoutCartEvent(Event):
    cart: Cart
    user_id: str = "user_default_buyer"
    approval_token: Optional[str] = None
    idempotency_key: Optional[str] = None
    reasoning_steps: List[Dict[str, Any]] = Field(default_factory=list)
    force_fail_payment: bool = False


class ApprovalConfirmationEvent(Event):
    user_id: str = "user_default_buyer"
    approval_token: str
    target_sku: Optional[str] = None
    idempotency_key: Optional[str] = None
    # State preservation fields
    include_bundle: bool = False
    force_fail_payment: bool = False
    max_price: Optional[float] = None
    user_query: str = ""


class RefundRequestEvent(Event):
    payment_id: str
    refund_amount: Optional[float] = None
    user_id: str = "user_default_buyer"
    reason: str = "Customer request"


class StatusQueryEvent(Event):
    query_type: str = "ORDER"  # ORDER or PAYMENT
    entity_id: str = ""
    user_id: str = "user_default_buyer"