import os

def write(filepath, content):
    d = os.path.dirname(filepath)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Wrote: {filepath}")

write('backend/app/workflows/events.py', '''from llama_index.core.workflow import Event
from typing import Optional, List, Dict, Any
from backend.app.models.cart import Cart, BundleOffer
from backend.app.models.catalog import Product
from backend.app.models.guardrail import PolicyEvaluationResult

class IntentClassifiedEvent(Event):
    intent: str # SEARCH, UPSELL, CART, CHECKOUT, PAYMENT, REFUND, CAMPAIGN, STATUS
    user_query: str
    extracted_entities: Dict[str, Any]
    user_id: str

class CatalogSearchEvent(Event):
    query: Optional[str]
    category: Optional[str]
    max_price: Optional[float]
    user_id: str

class CatalogResultEvent(Event):
    products: List[Product]
    user_query: str
    user_id: str

class UpsellEvent(Event):
    primary_product_id: str
    user_id: str
    user_query: Optional[str] = None

class UpsellResultEvent(Event):
    bundle: Optional[BundleOffer]
    user_id: str
    response_text: str

class CartAssembleEvent(Event):
    product_ids: List[str]
    quantities: List[int]
    bundle_id: Optional[str] = None
    user_id: str

class CartReadyEvent(Event):
    cart: Cart
    user_id: str
    intent: str

class GuardrailEvaluationEvent(Event):
    cart: Cart
    user_id: str
    idempotency_key: Optional[str] = None
    approval_token: Optional[str] = None

class GuardrailResultEvent(Event):
    cart: Cart
    policy_result: PolicyEvaluationResult
    user_id: str
    idempotency_key: Optional[str] = None

class RazorpayPaymentEvent(Event):
    order_id: str
    amount: float
    user_id: str
    method: str = "upi"
    force_fail: bool = False
''')

print("Workflow events written successfully!")
