import pytest, uuid
from backend.app.tools.read_tools import read_tools
from backend.app.tools.money_tools import money_tools
from backend.app.models.cart import Cart, CartItem
from backend.app.models.acp import ACPQuoteRequest, ACPCheckoutRequest
from backend.app.api.acp import get_machine_catalog, get_quote, execute_acp_checkout, get_mcp_tool_definitions

def test_acp_machine_catalog_readability():
    catalog_resp = get_machine_catalog()
    assert catalog_resp.protocol_version == "ACP/1.0"
    assert catalog_resp.currency == "INR"
    assert len(catalog_resp.catalog) >= 5
    for item in catalog_resp.catalog:
        assert item.sku.startswith("sku_")
        assert item.price_inr > 0
        assert len(item.spec_summary) > 0

def test_dynamic_upsell_calculation():
    bundle = read_tools.calculate_upsell_bundle("sku_kb_keychron_k2")
    assert bundle is not None
    assert bundle.complementary_product_id == "sku_acc_wrist_rest_walnut"
    assert bundle.discount_percentage == 5.0
    assert bundle.savings_amount > 0
    assert bundle.discounted_bundle_price < bundle.original_combined_price

def test_acp_quote_and_checkout_flow():
    # 1. Request Quote for a ScreenBar Light (₹2,299)
    quote_req = ACPQuoteRequest(
        skus=["sku_dev_screenbar_light"],
        quantities=[1],
        include_upsell_bundles=False,
        agent_id="ext_claude_buyer_01"
    )
    quote_resp = get_quote(quote_req)
    assert quote_resp.quote_id.startswith("quote_")
    assert quote_resp.total_amount == 2299.0
    assert quote_resp.guardrail_precheck == "PASS"

    # 2. Execute Programmatic Checkout
    checkout_req = ACPCheckoutRequest(
        quote_id=quote_resp.quote_id,
        idempotency_key=f"acp_test_{uuid.uuid4().hex[:8]}",
        buyer_agent_id="ext_claude_buyer_01"
    )
    checkout_resp = execute_acp_checkout(checkout_req)
    assert checkout_resp.status == "ORDER_CREATED"
    assert checkout_resp.order_id.startswith("order_")
    assert checkout_resp.amount == 2299.0
    assert checkout_resp.signature is not None

def test_mcp_tool_definitions_schema():
    schema = get_mcp_tool_definitions()
    assert schema["mcp_version"] == "2024-11-05"
    assert len(schema["tools"]) == 3
    tool_names = [t["name"] for t in schema["tools"]]
    assert "search_merchant_catalog" in tool_names
    assert "request_commerce_quote" in tool_names
    assert "execute_agentic_checkout" in tool_names
