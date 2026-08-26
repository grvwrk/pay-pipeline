import pytest
import asyncio
from backend.app.workflows.commerce_workflow import commerce_workflow
from backend.app.guardrails.policy_engine import policy_engine

@pytest.mark.anyio
async def test_workflow_catalog_discovery():
    res = await commerce_workflow.run(
        user_message="Show me mechanical keyboards under 5000",
        user_id="test_buyer_01"
    )
    assert res["type"] == "CATALOG_DISCOVERY"
    assert len(res["products"]) >= 1
    assert "Keychron" in res["message"] or "Royal Kludge" in res["message"] or "Ducky" in res["message"]
    assert res["upsell_bundle"] is not None

@pytest.mark.anyio
async def test_workflow_guardrail_denial():
    # Attempting to buy ₹7,999 keyboard with ₹5,000 spend limit
    res = await commerce_workflow.run(
        user_message="Buy me the AeroPro CNC Anodized Aluminium Gasket Keyboard for 7999",
        user_id="test_buyer_01"
    )
    assert res["type"] == "GUARDRAIL_DENIED"
    assert res["decision_code"] == "DENIED_SPEND_LIMIT"
    assert "exceeds" in res["message"]

@pytest.mark.anyio
async def test_workflow_gated_approval_flow():
    # Attempting to buy ₹4,499 item (> ₹3,000 threshold) without approval token
    res = await commerce_workflow.run(
        user_message="Buy Keychron K2 mechanical keyboard for 4499",
        user_id="test_buyer_01"
    )
    assert res["type"] == "APPROVAL_REQUIRED"
    assert res["approval_token"] is not None
    assert "threshold" in res["message"] or "confirmation" in res["message"]

@pytest.mark.anyio
async def test_workflow_approval_token_confirmation():
    # Confirming order with valid approval token
    token = "appr_tok_test_valid_123"
    res = await commerce_workflow.run(
        user_message="Approve and proceed with order",
        user_id="test_buyer_01",
        approval_token=token,
        sku="sku_kb_keychron_k2"
    )
    assert res["type"] == "ORDER_CREATED"
    assert res["order"] is not None
    assert res["order"]["order_id"].startswith("order_")

@pytest.mark.anyio
async def test_workflow_direct_order_within_limits():
    # Buying ₹1,899 vertical mouse (under ₹3,000 approval threshold and ₹5,000 limit)
    res = await commerce_workflow.run(
        user_message="Buy AeroGrip Ergonomic Wireless Vertical Mouse",
        user_id="test_buyer_01"
    )
    assert res["type"] == "ORDER_CREATED"
    assert res["order"] is not None
    assert res["order"]["amount"] == 1899.0
