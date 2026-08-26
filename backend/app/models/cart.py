from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid

class CartItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int = 1
    subtotal: float
    category: str = ""
    specs: Dict[str, Any] = Field(default_factory=dict)

class BundleOffer(BaseModel):
    bundle_id: str
    title: str
    description: str
    primary_product_id: str
    primary_product_name: str
    complementary_product_id: str
    complementary_product_name: str
    original_combined_price: float
    discounted_bundle_price: float
    savings_amount: float
    discount_percentage: float
    rationale: str

class Cart(BaseModel):
    cart_id: str = Field(default_factory=lambda: f"cart_{uuid.uuid4().hex[:10]}")
    user_id: str = "user_default_buyer"
    items: List[CartItem] = Field(default_factory=list)
    subtotal: float = 0.0
    discount_amount: float = 0.0
    applied_bundle: Optional[BundleOffer] = None
    shipping_fee: float = 0.0
    total_amount: float = 0.0
    currency: str = "INR"

    def recalculate(self):
        self.subtotal = sum(item.subtotal for item in self.items)
        if self.applied_bundle:
            self.discount_amount = self.applied_bundle.savings_amount
        else:
            self.discount_amount = 0.0
        self.total_amount = max(0.0, self.subtotal - self.discount_amount + self.shipping_fee)
