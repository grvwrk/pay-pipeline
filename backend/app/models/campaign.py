from pydantic import BaseModel, Field
from typing import List, Optional

class CustomerSegment(BaseModel):
    id: str
    name: str
    description: str
    affinity_categories: List[str]
    average_order_value: float
    customer_count: int
    upsell_propensity_score: float # 0.0 to 1.0

class Campaign(BaseModel):
    id: str
    title: str
    target_segment: str
    trigger_condition: str
    bundle_offer: str
    discount_percentage: float
    max_budget_inr: float
    spent_budget_inr: float = 0.0
    conversions: int = 0
    revenue_generated_inr: float = 0.0
    status: str = "ACTIVE" # ACTIVE, PAUSED, COMPLETED
