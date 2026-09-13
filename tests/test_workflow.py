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
async def test_workflow_peanut_butter_highest_protein_query():
    # User intent: "best available peanut butter with highest protein % under 700rs"
    res = await commerce_workflow.run(
        user_message="best available peanut butter with highest protein % under 700rs",
        user_id="test_buyer_01"
    )
    assert res["type"] == "CATALOG_DISCOVERY"
    assert len(res["products"]) >= 1
    # Pintola with 36% Protein Isolate must be top recommendation
    assert "Pintola" in res["top_choice"]["name"]
    assert res["top_choice"]["price"] <= 700.0
    assert "36%" in res["top_choice"]["specs"]["protein_percentage"]
    assert res["upsell_bundle"] is not None

@pytest.mark.anyio
async def test_workflow_running_shoes_query():
    res = await commerce_workflow.run(
        user_message="Find me running shoes for long distance under 5000 rs",
        user_id="test_buyer_01"
    )
    assert res["type"] == "CATALOG_DISCOVERY"
    assert len(res["products"]) >= 1
    assert "Nike" in res["top_choice"]["name"]
    assert res["top_choice"]["price"] <= 5000.0

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
    # A token only unlocks the gate if the policy engine actually issued it, so
    # the gate has to be tripped first to obtain one.
    gated = await commerce_workflow.run(
        user_message="Buy the Keychron K2",
        user_id="test_buyer_01",
        sku="sku_kb_keychron_k2"
    )
    assert gated["type"] == "APPROVAL_REQUIRED"
    token = gated["approval_token"]
    assert token

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
async def test_workflow_fabricated_approval_token_is_rejected():
    """An approval token the engine never issued must not unlock a gated purchase."""
    res = await commerce_workflow.run(
        user_message="Approve and proceed with order",
        user_id="test_buyer_forged",
        approval_token="appr_tok_not_issued_by_the_engine",
        sku="sku_kb_keychron_k2"
    )
    assert res["type"] != "ORDER_CREATED"
    assert res["type"] == "APPROVAL_REQUIRED"

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

@pytest.mark.anyio
async def test_workflow_delegates_checkout_to_policy_agent():
    res = await commerce_workflow.run(
        user_message="Buy AeroGrip Ergonomic Wireless Vertical Mouse",
        user_id="test_multi_agent_buyer"
    )
    assert res["type"] == "ORDER_CREATED"
    agents = [step["agent_name"] for step in res["reasoning_steps"]]
    # The checkout agent opens the trace and the policy agent closes it: the
    # untrusted side never gets the last word on whether money moves. Steps in
    # between (product selection, upsell) may vary, so this asserts the
    # delegation contract rather than an exact transcript.
    assert agents[0] == "Checkout Agent"
    assert agents[-1] == "Guardrail & Policy Agent"
    assert set(agents) <= {"Checkout Agent", "Upsell Agent", "Guardrail & Policy Agent"}
