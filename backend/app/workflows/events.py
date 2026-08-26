from llama_index.core.workflow import Event
from typing import Optional, List, Dict, Any
from backend.app.models.cart import Cart, BundleOffer
from backend.app.models.catalog import Product
from backend.app.models.guardrail import PolicyEvaluationResult

class IntentClassifiedEvent(Event):
    intent: str  # SEARCH, UPSELL, BUY, APPROVE, REFUND, CAMPAIGN, STATUS
    user_query: str
    user_id: str
    target_sku: Optional[str] = None
    target_category: Optional[str] = None
    max_price: Optional[float] = None
    include_bundle: bool = False
    approval_token: Optional[str] = None
    idempotency_key: Optional[str] = None
    force_fail_payment: bool = False

class CatalogSearchEvent(Event):
    query: Optional[str]
    category: Optional[str]
    max_price: Optional[float]
    user_id: str
    include_bundle_analysis: bool = True

class CatalogResultEvent(Event):
    products: List[Product]
    top_choice: Optional[Product]
    upsell_bundle: Optional[BundleOffer]
    user_query: str
    user_id: str

class UpsellEvent(Event):
    primary_product: Product
    user_id: str
    user_query: Optional[str] = None

class UpsellResultEvent(Event):
    primary_product: Product
    bundle: Optional[BundleOffer]
    user_id: str
    recommendation_text: str

class CheckoutEvent(Event):
    user_id: str
    target_sku: Optional[str] = None
    query: Optional[str] = None
    max_price: Optional[float] = None
    include_bundle: bool = False
    approval_token: Optional[str] = None
    idempotency_key: Optional[str] = None
    force_fail_payment: bool = False

class ApprovalConfirmationEvent(Event):
    user_id: str
    approval_token: str
    target_sku: Optional[str] = None
    idempotency_key: Optional[str] = None
