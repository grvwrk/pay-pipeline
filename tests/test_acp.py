import pytest
from backend.app.tools.read_tools import read_tools
from backend.app.tools.money_tools import money_tools
from backend.app.models.cart import Cart, CartItem

def test_acp_machine_catalog_readability():
    catalog = read_tools.catalog
    assert len(catalog) >= 5
    for item in catalog:
        assert item.id.startswith("sku_")
        assert item.price > 0
        assert item.currency == "INR"
        assert len(item.specs) > 0

def test_dynamic_upsell_calculation():
    bundle = read_tools.calculate_upsell_bundle("sku_kb_keychron_k2")
    assert bundle is not None
    assert bundle.complementary_product_id == "sku_acc_wrist_rest_walnut"
    assert bundle.discount_percentage == 5.0
    assert bundle.savings_amount > 0
    assert bundle.discounted_bundle_price < bundle.original_combined_price
