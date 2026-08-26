from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Product(BaseModel):
    id: str = Field(..., description="Unique Product SKU/ID")
    name: str = Field(..., description="Product display name")
    category: str = Field(..., description="Category classification")
    price: float = Field(..., description="Price in INR")
    currency: str = Field("INR", description="Currency code")
    inventory: int = Field(..., description="Available stock count")
    rating: float = Field(4.5, description="Product customer rating (0-5)")
    review_count: int = Field(0, description="Number of verified reviews")
    shipping_eta_hours: int = Field(24, description="Expected dispatch time in hours")
    tags: List[str] = Field(default_factory=list, description="Search and semantic tags")
    specs: Dict[str, Any] = Field(default_factory=dict, description="Technical specifications")
    complementary_product_ids: List[str] = Field(default_factory=list, description="Affinity product IDs for upsell/cross-sell")
    image_url: Optional[str] = None
    description: str = ""

class ProductFilter(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    max_price: Optional[float] = None
    min_rating: Optional[float] = None
    in_stock_only: bool = True
    tags: Optional[List[str]] = None
