import pytest
from backend.app.tools.discount_engine import discount_engine
from backend.app.models.cart import BundleOffer


def test_tier_1_volume_discount():
    # ₹4,000 cart: 10% is ₹400 (under ₹500 cap)
    calc = discount_engine.calculate_discount(subtotal=4000.0)
    assert calc.calculated_discount == 400.0
    assert calc.final_total == 3600.0

    # ₹6,000 cart: 10% is ₹600 -> capped at ₹500
    calc_capped = discount_engine.calculate_discount(subtotal=6000.0)
    assert calc_capped.calculated_discount == 500.0
    assert calc_capped.final_total == 5500.0


def test_bundle_discount():
    bundle = BundleOffer(
        primary_product_id="sku_kb_keychron_k2",
        primary_product_name="Keychron K2",
        complementary_product_id="sku_acc_wrist_rest_walnut",
        complementary_product_name="Walnut Rest",
        original_combined_price=4998.0,
        discounted_bundle_price=4973.05,
        savings_amount=24.95,
        rationale="5% accessory savings"
    )
    calc = discount_engine.calculate_discount(subtotal=4998.0, bundle=bundle)
    assert calc.calculated_discount == 24.95
    assert calc.final_total == 4973.05


def test_promo_code_discount():
    calc = discount_engine.calculate_discount(subtotal=3000.0, promo_code="GROWTH10")
    assert calc.calculated_discount == 300.0
    assert calc.final_total == 2700.0
