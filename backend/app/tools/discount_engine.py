from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.app.models.cart import Cart, BundleOffer


class DiscountBreakdown(BaseModel):
    subtotal: float
    discount_rate: float = 0.0
    calculated_discount: float = 0.0
    max_discount: float = 0.0
    final_discount: float = 0.0
    final_total: float
    applied_rules: List[str] = Field(default_factory=list)


class DeterministicDiscountEngine:
    """
    Deterministic Discount Engine.
    Evaluates tiered cart discounts, dynamic accessory bundle savings,
    and promo rules bounded by merchant policy. Never trusts LLM-generated amounts.
    """

    # Configurable merchant discount rules
    TIER_1_THRESHOLD: float = 3000.0
    TIER_1_RATE: float = 0.10          # 10% discount on carts > ₹3,000
    TIER_1_MAX_CAP: float = 500.0      # Capped at ₹500 max

    BUNDLE_DISCOUNT_RATE: float = 0.05  # 5% discount on bundled accessories

    PROMO_CODES = {
        "GROWTH10": {"rate": 0.10, "max_discount": 500.0, "min_subtotal": 2000.0},
        "SAVE15": {"rate": 0.15, "max_discount": 750.0, "min_subtotal": 4000.0},
    }

    def calculate_discount(
        self,
        subtotal: float,
        bundle: Optional[BundleOffer] = None,
        promo_code: Optional[str] = None
    ) -> DiscountBreakdown:
        if subtotal <= 0:
            return DiscountBreakdown(subtotal=0.0, final_total=0.0)

        total_discount = 0.0
        applied_rules: List[str] = []
        effective_rate = 0.0

        # 1. Evaluate Bundle Savings if present
        if bundle and bundle.savings_amount > 0:
            bundle_savings = bundle.savings_amount
            total_discount += bundle_savings
            applied_rules.append(f"Complementary accessory bundle discount: ₹{bundle_savings:.2f}")

        # 2. Evaluate Tiered Volume Discount (if no bundle discount already applied)
        elif subtotal >= self.TIER_1_THRESHOLD:
            calc_tier = subtotal * self.TIER_1_RATE
            tier_discount = min(calc_tier, self.TIER_1_MAX_CAP)
            total_discount += tier_discount
            effective_rate = self.TIER_1_RATE
            applied_rules.append(f"Tier 1 volume discount (10% over ₹3,000, capped at ₹500): ₹{tier_discount:.2f}")

        # 3. Evaluate Promo Code (optional override/addition)
        if promo_code and promo_code.upper() in self.PROMO_CODES:
            p_rule = self.PROMO_CODES[promo_code.upper()]
            if subtotal >= p_rule["min_subtotal"]:
                promo_calc = subtotal * p_rule["rate"]
                promo_discount = min(promo_calc, p_rule["max_discount"])
                # Apply the better discount
                if promo_discount > total_discount:
                    total_discount = promo_discount
                    effective_rate = p_rule["rate"]
                    applied_rules = [f"Promo code {promo_code.upper()}: ₹{promo_discount:.2f}"]

        # Guard against negative total
        total_discount = min(total_discount, subtotal)
        final_total = max(0.0, subtotal - total_discount)

        return DiscountBreakdown(
            subtotal=round(subtotal, 2),
            discount_rate=effective_rate,
            calculated_discount=round(total_discount, 2),
            max_discount=self.TIER_1_MAX_CAP,
            final_discount=round(total_discount, 2),
            final_total=round(final_total, 2),
            applied_rules=applied_rules
        )


discount_engine = DeterministicDiscountEngine()
