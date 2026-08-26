import pytest
import asyncio
from backend.app.workflows.commerce_workflow import commerce_workflow

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
    # Attempting to buy 7999 keyboard with 5000 limit
    res = await commerce_workflow.run(
        user_message="Buy me the AeroPro CNC Anodized Aluminium Gasket Keyboard for 7999",
        user_id="test_buyer_01"
    )
    assert res["type"] == "GUARDRAIL_DENIED"
    assert res["decision_code"] == "DENIED_SPEND_LIMIT"
    assert "exceeds" in res["message"]
