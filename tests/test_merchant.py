import pytest
from backend.app.api.merchant import get_merchant_analytics, create_campaign
from backend.app.models.campaign import Campaign

def test_merchant_growth_kpis():
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
