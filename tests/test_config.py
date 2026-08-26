import os
import tempfile
from pathlib import Path
import pytest
import yaml
from backend.app.config import Settings, load_settings, settings, _find_config_file


def test_default_config_loaded():
    """Verify that settings are loaded properly with default values and config.yaml data."""
    assert settings.PROJECT_NAME == "pay-pipeline - Agentic Commerce & Revenue Growth Engine"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.DEFAULT_MAX_TXN_AMOUNT_INR == 5000.0
    assert settings.DEFAULT_MAX_CUMULATIVE_SPEND_INR == 15000.0
    assert settings.DEFAULT_APPROVAL_THRESHOLD_INR == 3000.0
    assert settings.DEFAULT_MAX_ITEM_QUANTITY == 5
    assert settings.ALLOWED_CURRENCY == "INR"
    assert "mechanical_keyboards" in settings.ALLOWED_CATEGORIES
    assert settings.MERCHANT_ID == "merch_pay_pipeline_01"
    assert settings.AUDIT_HMAC_SECRET is not None
    assert len(settings.AUDIT_HMAC_SECRET) > 0


def test_custom_yaml_loading():
    """Verify loading settings from a custom YAML file."""
    custom_yaml = """
server:
  project_name: "Custom Test Store"
  port: 9000
  host: "127.0.0.1"

payment:
  provider_mode: "razorpay"
  razorpay_key_id: "rzp_test_custom_123"
  razorpay_key_secret: "rzp_sec_custom_456"
  razorpay_webhook_secret: "webhook_custom_secret_789"

audit:
  hmac_secret: "audit_custom_secret_abc"

guardrails:
  max_transaction_amount_inr: 8000.0
  max_cumulative_spend_inr: 25000.0
  approval_threshold_inr: 4500.0
  max_item_quantity: 10
  allowed_currency: "INR"
  allowed_categories:
    - "custom_category_1"

merchant:
  merchant_id: "merch_custom_007"
  merchant_name: "Custom Boutique"
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tf:
        tf.write(custom_yaml)
        temp_path = tf.name

    try:
        cfg = load_settings(config_path=temp_path)
        assert cfg.PROJECT_NAME == "Custom Test Store"
        assert cfg.PORT == 9000
        assert cfg.HOST == "127.0.0.1"
        assert cfg.PAYMENT_PROVIDER_MODE == "razorpay"
        assert cfg.RAZORPAY_KEY_ID == "rzp_test_custom_123"
        assert cfg.RAZORPAY_KEY_SECRET == "rzp_sec_custom_456"
        assert cfg.RAZORPAY_WEBHOOK_SECRET == "webhook_custom_secret_789"
        assert cfg.AUDIT_HMAC_SECRET == "audit_custom_secret_abc"
        assert cfg.DEFAULT_MAX_TXN_AMOUNT_INR == 8000.0
        assert cfg.DEFAULT_MAX_CUMULATIVE_SPEND_INR == 25000.0
        assert cfg.DEFAULT_APPROVAL_THRESHOLD_INR == 4500.0
        assert cfg.DEFAULT_MAX_ITEM_QUANTITY == 10
        assert cfg.ALLOWED_CATEGORIES == ["custom_category_1"]
        assert cfg.MERCHANT_ID == "merch_custom_007"
        assert cfg.MERCHANT_NAME == "Custom Boutique"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_env_var_overrides(monkeypatch):
    """Verify that environment variables override values from YAML."""
    monkeypatch.setenv("PROJECT_NAME", "Env Override Store")
    monkeypatch.setenv("PORT", "9999")
    monkeypatch.setenv("PAYMENT_PROVIDER_MODE", "razorpay")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_env_override_key")
    monkeypatch.setenv("DEFAULT_MAX_TXN_AMOUNT_INR", "6500.0")
    monkeypatch.setenv("ENABLE_GROQ_BROWSER_SEARCH", "true")

    cfg = load_settings()
    assert cfg.PROJECT_NAME == "Env Override Store"
    assert cfg.PORT == 9999
    assert cfg.PAYMENT_PROVIDER_MODE == "razorpay"
    assert cfg.RAZORPAY_KEY_ID == "rzp_env_override_key"
    assert cfg.DEFAULT_MAX_TXN_AMOUNT_INR == 6500.0
    assert cfg.ENABLE_GROQ_BROWSER_SEARCH is True


def test_missing_or_invalid_yaml_fallback():
    """Verify graceful fallback when YAML file is missing or invalid."""
    # Non-existent file
    cfg_missing = load_settings(config_path="/non/existent/path/config.yaml")
    assert cfg_missing.PROJECT_NAME == "pay-pipeline - Agentic Commerce & Revenue Growth Engine"
    assert cfg_missing.DEFAULT_MAX_TXN_AMOUNT_INR == 5000.0

    # Malformed YAML file
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tf:
        tf.write("server: [unclosed list")
        temp_path = tf.name

    try:
        cfg_invalid = load_settings(config_path=temp_path)
        assert cfg_invalid.PROJECT_NAME == "pay-pipeline - Agentic Commerce & Revenue Growth Engine"
        assert cfg_invalid.PORT == 8000
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
