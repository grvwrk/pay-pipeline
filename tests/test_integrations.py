import pytest

from backend.app.llm.groq_agent import groq_catalog_agent
from backend.app.payment.razorpay_client import RazorpayApiError, RazorpayClientWrapper


def test_catalog_agent_is_offline_without_groq_configuration():
    result = groq_catalog_agent.run("mechanical keyboard", "mechanical_keyboards", 5000)
    assert result.provider == "deterministic"
    assert result.products


def test_razorpay_mode_requires_environment_credentials(monkeypatch):
    from backend.app.config import settings
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER_MODE", "razorpay")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", None)
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", None)
    client = RazorpayClientWrapper()
    with pytest.raises(RazorpayApiError, match="RAZORPAY_KEY_ID"):
        client.create_order(100.0, "cart_test")
