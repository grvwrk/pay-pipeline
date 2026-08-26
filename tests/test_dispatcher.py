import pytest
from backend.app.tools.dispatcher import tool_dispatcher, ToolRiskLevel


def test_tool_dispatcher_risk_and_execution():
    res = tool_dispatcher.execute("get_product", {"product_id": "sku_kb_keychron_k2"})
    assert res.success
    assert res.risk_level == ToolRiskLevel.LOW
    assert res.data is not None
    assert "Keychron K2" in res.data.name
    assert res.latency_ms >= 0.0


def test_tool_dispatcher_unknown_tool_rejection():
    res = tool_dispatcher.execute("unauthorized_money_mover", {"amount": 99999})
    assert not res.success
    assert "Unauthorized or unrecognized tool" in res.error
    assert res.guardrail_decision == "REJECTED"
