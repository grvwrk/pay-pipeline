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
    bundle_id: str = Field(default_factory=lambda: f"bndl_{uuid.uuid4().hex[:8]}")
    title: str = "Complementary Accessory Bundle"
    description: str = "Authorized 5% bundle discount"
    primary_product_id: str
    primary_product_name: str
    complementary_product_id: str
    complementary_product_name: str
    original_combined_price: float
    discounted_bundle_price: float
    savings_amount: float
    discount_percentage: float = 5.0
    rationale: str = ""

    @property
    def original_bundle_price(self) -> float:
        return self.original_combined_price

    @property
    def upsell_rationale(self) -> str:
        return self.rationale


class Cart(BaseModel):
    cart_id: str = Field(default_factory=lambda: f"cart_{uuid.uuid4().hex[:10]}")
    user_id: str = "user_default_buyer"
    items: List[CartItem] = Field(default_factory=list)
    subtotal_amount: float = 0.0
    discount_amount: float = 0.0
    applied_bundle: Optional[BundleOffer] = None
    shipping_fee: float = 0.0
    total_amount: float = 0.0
    currency: str = "INR"

    @property
    def subtotal(self) -> float:
        return self.subtotal_amount

    @subtotal.setter
    def subtotal(self, val: float):
        self.subtotal_amount = val

    def recalculate(self):
        self.subtotal_amount = round(sum(item.price * item.quantity for item in self.items), 2)
        if self.applied_bundle:
            self.discount_amount = round(self.applied_bundle.savings_amount, 2)
        self.total_amount = round(max(0.0, self.subtotal_amount - self.discount_amount + self.shipping_fee), 2)
