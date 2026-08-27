import pytest
from backend.app.tools.search_tools import tavily_search_engine, TavilySearchEngine
from backend.app.tools.dispatcher import tool_dispatcher, ToolRiskLevel


def test_tavily_search_engine_basic():
    # Test query execution
    res = tavily_search_engine.search("Keychron K2 specifications and switches", max_results=3)
    assert res is not None
    assert "results" in res
    assert len(res["results"]) > 0
    assert "title" in res["results"][0]
    assert "snippet" in res["results"][0]
    assert "url" in res["results"][0]


def test_tavily_search_registered_in_dispatcher():
    res = tool_dispatcher.execute(
        "tavily_search",
        {"query": "Pintola high protein peanut butter", "max_results": 2},
        context={"user_id": "test_user_01"}
    )
    assert res.success
    assert res.risk_level == ToolRiskLevel.LOW
    assert res.data is not None
    assert "results" in res.data
    assert res.latency_ms >= 0.0


def test_web_search_alias_in_dispatcher():
    res = tool_dispatcher.execute(
        "web_search",
        {"query": "Nike Pegasus 40 running shoe specs", "max_results": 2},
        context={"user_id": "test_user_01"}
    )
    assert res.success
    assert res.risk_level == ToolRiskLevel.LOW
    assert res.data is not None
