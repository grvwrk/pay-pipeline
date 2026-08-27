import pytest
from backend.app.api.merchant import get_merchant_analytics, create_campaign
from backend.app.models.campaign import Campaign

from backend.app.database.db import init_db
from backend.app.database.repositories import order_repo, cart_repo
from backend.app.models.order import RazorpayOrder, TransactionState
from backend.app.models.cart import Cart

def test_merchant_growth_kpis():
    init_db()
    
    # Seed a cart
    cart = Cart(cart_id="cart_test_merchant_123", user_id="user_merchant_123")
    cart_repo.save_cart(cart)
    
    # Seed a captured order with bundle applied and amount > baseline_aov (3000)
    order = RazorpayOrder(
        order_id="order_test_merchant_123",
        cart_id="cart_test_merchant_123",
        amount=4500.0,
        amount_in_paise=450000,
        currency="INR",
        status="paid",
        receipt="rcpt_merchant_123",
        state=TransactionState.PAYMENT_CAPTURED,
        notes={"user_id": "user_merchant_123", "bundle_applied": "true"}
    )
    order_repo.create_order(order)

    data = get_merchant_analytics()
    assert "kpis" in data
    kpis = data["kpis"]
    assert kpis["average_order_value_inr"] > kpis["baseline_aov_without_agent_inr"]
    assert kpis["aov_growth_percentage"] > 0
    assert kpis["upsell_conversion_rate"] > 0
    assert "segments" in data
    assert "campaigns" in data

def test_merchant_campaign_creation():
    camp = Campaign(
        id="camp_test_growth_01",
        title="Developer Setup Bundle Blitz",
        target_segment="Developers & Remote Workers",
        trigger_condition="CART_SUBTOTAL_EXCEEDS_3000",
        bundle_offer="Keychron K2 + Walnut Wrist Rest (5% OFF)",
        discount_percentage=5.0,
        max_budget_inr=10000.0,
        spent_budget_inr=0.0,
        status="ACTIVE"
    )
    res = create_campaign(camp)
    assert res["status"] == "SUCCESS"
    assert "activated" in res["message"]
