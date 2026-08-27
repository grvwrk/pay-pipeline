import os
import secrets
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml
from pydantic import BaseModel, Field


def _find_config_file(custom_path: Optional[str] = None) -> Optional[Path]:
    """Find the path to config.yaml looking in custom path, env vars, and standard locations."""
    if custom_path and Path(custom_path).is_file():
        return Path(custom_path).resolve()

    env_path = os.getenv("CONFIG_PATH") or os.getenv("CONFIG_FILE")
    if env_path and Path(env_path).is_file():
        return Path(env_path).resolve()

    current_file = Path(__file__).resolve()
    candidates = [
        Path.cwd() / "config.yaml",
        Path.cwd() / "config.yml",
        current_file.parent.parent.parent / "config.yaml",
        current_file.parent.parent.parent / "config.yml",
        current_file.parent / "config.yaml",
        current_file.parent.parent / "config.yaml",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    return None


def _load_yaml_dict(file_path: Optional[Path]) -> Dict[str, Any]:
    """Safely load and parse YAML file content."""
    if not file_path or not file_path.is_file():
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"[Config] Warning: Failed to parse YAML at {file_path}: {e}")
        return {}


class Settings(BaseModel):
    # Server & API
    PROJECT_NAME: str = "pay-pipeline - Agentic Commerce & Revenue Growth Engine"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Database
    DATABASE_URL: str = "sqlite:///./pay_pipeline.db"
    CATALOG_DB_PATH: str = "backend/app/data/catalog_db.json"

    # Credentials & Payment Rail
    PAYMENT_PROVIDER_MODE: str = "simulator"
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_WEBHOOK_SECRET: str = Field(default_factory=lambda: secrets.token_urlsafe(32))

    # Cryptographic Audit Secret
    AUDIT_HMAC_SECRET: str = Field(default_factory=lambda: secrets.token_urlsafe(32))

    # Groq LLM & Agents
    LLM_PROVIDER: str = "deterministic"
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_MAX_TOOL_ROUNDS: int = 4
    ENABLE_GROQ_BROWSER_SEARCH: bool = True

    # Search & Market Intelligence (Tavily)
    SEARCH_PROVIDER: str = "tavily"
    TAVILY_API_KEY: Optional[str] = None
    MAX_SEARCH_RESULTS: int = 5

    # Deterministic Guardrail Defaults
    DEFAULT_MAX_TXN_AMOUNT_INR: float = 5000.0        # Hard ceiling per single transaction
    DEFAULT_MAX_CUMULATIVE_SPEND_INR: float = 15000.0   # Cumulative session ceiling
    DEFAULT_APPROVAL_THRESHOLD_INR: float = 3000.0     # Orders > ₹3,000 require gated human confirmation
    DEFAULT_MAX_ITEM_QUANTITY: int = 5
    ALLOWED_CURRENCY: str = "INR"
    ALLOWED_CATEGORIES: List[str] = Field(default_factory=lambda: [
        "smartphones",
        "mobile_accessories",
        "mechanical_keyboards",
        "computer_peripherals",
        "workspace_accessories",
        "developer_gear",
        "ergonomics",
        "audio_equipment",
        "nutrition_and_fitness",
        "running_shoes",
        "health_and_groceries"
    ])

    # Merchant Metadata
    MERCHANT_ID: str = "merch_pay_pipeline_01"
    MERCHANT_NAME: str = "pay-pipeline Store"

    # Source metadata
    CONFIG_FILE_PATH: Optional[str] = None

    # Discount Engine configuration
    DISCOUNT_TIER_1_THRESHOLD: float = 3000.0
    DISCOUNT_TIER_1_RATE: float = 0.10
    DISCOUNT_TIER_1_MAX_CAP: float = 500.0
    DISCOUNT_BUNDLE_DISCOUNT_RATE: float = 0.05
    DISCOUNT_PROMO_CODES: Dict[str, Dict[str, float]] = Field(default_factory=lambda: {
        "GROWTH10": {"rate": 0.10, "max_discount": 500.0, "min_subtotal": 2000.0},
        "SAVE15": {"rate": 0.15, "max_discount": 750.0, "min_subtotal": 4000.0},
    })

    # Payment Links defaults
    PAYMENT_CUSTOMER_NAME: str = "pay-pipeline Buyer"
    PAYMENT_CUSTOMER_CONTACT: str = "+919999999999"
    PAYMENT_CUSTOMER_EMAIL: str = "buyer@pay-pipeline.com"

    # ACP configurations
    ACP_QUOTE_EXPIRATION_SECONDS: int = 300

    # Merchant analytics
    MERCHANT_BASELINE_AOV_INR: float = 3000.0


def load_settings(config_path: Optional[str] = None) -> Settings:
    """
    Construct and return a Settings instance by layering:
    1. Base defaults
    2. config.yaml configuration
    3. Environment variable overrides
    """
    cfg_file = _find_config_file(config_path)
    yaml_data = _load_yaml_dict(cfg_file)

    server_cfg = yaml_data.get("server", {})
    db_cfg = yaml_data.get("database", {})
    payment_cfg = yaml_data.get("payment", {})
    audit_cfg = yaml_data.get("audit", {})
    llm_cfg = yaml_data.get("llm", {})
    search_cfg = yaml_data.get("search", {})
    guardrails_cfg = yaml_data.get("guardrails", {})
    merchant_cfg = yaml_data.get("merchant", {})
    discount_cfg = yaml_data.get("discount", {})

    def _parse_bool(val: Any) -> bool:
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "1", "yes", "on")

    def _parse_int(val: Any, default: int) -> int:
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def _parse_float(val: Any, default: float) -> float:
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    # 1. Server settings
    project_name = (
        os.getenv("PROJECT_NAME")
        or server_cfg.get("project_name")
        or yaml_data.get("PROJECT_NAME")
        or "pay-pipeline - Agentic Commerce & Revenue Growth Engine"
    )
    api_v1_str = (
        os.getenv("API_V1_STR")
        or server_cfg.get("api_v1_str")
        or yaml_data.get("API_V1_STR")
        or "/api/v1"
    )
    host = (
        os.getenv("HOST")
        or server_cfg.get("host")
        or yaml_data.get("HOST")
        or "0.0.0.0"
    )
    port = _parse_int(
        os.getenv("PORT") or server_cfg.get("port") or yaml_data.get("PORT"),
        default=8000
    )

    # Database
    db_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("DB_URL")
        or db_cfg.get("db_url")
        or yaml_data.get("DATABASE_URL")
        or "sqlite:///./pay_pipeline.db"
    )
    catalog_db_path = (
        os.getenv("CATALOG_DB_PATH")
        or db_cfg.get("catalog_db_path")
        or yaml_data.get("CATALOG_DB_PATH")
        or "backend/app/data/catalog_db.json"
    )

    # 2. Payment settings
    payment_provider_mode = (
        os.getenv("PAYMENT_PROVIDER_MODE")
        or payment_cfg.get("provider_mode")
        or yaml_data.get("PAYMENT_PROVIDER_MODE")
        or "simulator"
    ).lower()

    razorpay_key_id = (
        os.getenv("RAZORPAY_KEY_ID")
        or payment_cfg.get("razorpay_key_id")
        or yaml_data.get("RAZORPAY_KEY_ID")
    )
    razorpay_key_secret = (
        os.getenv("RAZORPAY_KEY_SECRET")
        or payment_cfg.get("razorpay_key_secret")
        or yaml_data.get("RAZORPAY_KEY_SECRET")
    )
    razorpay_webhook_secret = (
        os.getenv("RAZORPAY_WEBHOOK_SECRET")
        or payment_cfg.get("razorpay_webhook_secret")
        or yaml_data.get("RAZORPAY_WEBHOOK_SECRET")
        or secrets.token_urlsafe(32)
    )

    # 3. Audit settings
    audit_hmac_secret = (
        os.getenv("AUDIT_HMAC_SECRET")
        or audit_cfg.get("hmac_secret")
        or audit_cfg.get("audit_hmac_secret")
        or yaml_data.get("AUDIT_HMAC_SECRET")
        or secrets.token_urlsafe(32)
    )

    # 4. LLM & Agent settings
    llm_provider = (
        os.getenv("LLM_PROVIDER")
        or llm_cfg.get("provider")
        or yaml_data.get("LLM_PROVIDER")
        or "deterministic"
    ).lower()

    groq_api_key = (
        os.getenv("GROQ_API_KEY")
        or llm_cfg.get("groq_api_key")
        or yaml_data.get("GROQ_API_KEY")
    )
    groq_model = (
        os.getenv("GROQ_MODEL")
        or llm_cfg.get("groq_model")
        or yaml_data.get("GROQ_MODEL")
        or "openai/gpt-oss-20b"
    )
    groq_max_tool_rounds = _parse_int(
        os.getenv("GROQ_MAX_TOOL_ROUNDS") or llm_cfg.get("groq_max_tool_rounds") or yaml_data.get("GROQ_MAX_TOOL_ROUNDS"),
        default=4
    )
    enable_groq_browser_search = _parse_bool(
        os.getenv("ENABLE_GROQ_BROWSER_SEARCH")
        if os.getenv("ENABLE_GROQ_BROWSER_SEARCH") is not None
        else llm_cfg.get("enable_groq_browser_search", yaml_data.get("ENABLE_GROQ_BROWSER_SEARCH", True))
    )

    # 5. Search & Market Intelligence (Tavily)
    search_provider = (
        os.getenv("SEARCH_PROVIDER")
        or search_cfg.get("provider")
        or yaml_data.get("SEARCH_PROVIDER")
        or "tavily"
    ).lower()
    tavily_api_key = (
        os.getenv("TAVILY_API_KEY")
        or search_cfg.get("tavily_api_key")
        or yaml_data.get("TAVILY_API_KEY")
    )
    max_search_results = _parse_int(
        os.getenv("MAX_SEARCH_RESULTS")
        or search_cfg.get("max_search_results")
        or yaml_data.get("MAX_SEARCH_RESULTS"),
        default=5
    )

    # 6. Guardrail defaults
    default_max_txn = _parse_float(
        os.getenv("DEFAULT_MAX_TXN_AMOUNT_INR")
        or guardrails_cfg.get("max_transaction_amount_inr")
        or guardrails_cfg.get("default_max_txn_amount_inr")
        or yaml_data.get("DEFAULT_MAX_TXN_AMOUNT_INR"),
        default=5000.0
    )
    default_max_cumulative = _parse_float(
        os.getenv("DEFAULT_MAX_CUMULATIVE_SPEND_INR")
        or guardrails_cfg.get("max_cumulative_spend_inr")
        or guardrails_cfg.get("default_max_cumulative_spend_inr")
        or yaml_data.get("DEFAULT_MAX_CUMULATIVE_SPEND_INR"),
        default=15000.0
    )
    default_approval_threshold = _parse_float(
        os.getenv("DEFAULT_APPROVAL_THRESHOLD_INR")
        or guardrails_cfg.get("approval_threshold_inr")
        or guardrails_cfg.get("default_approval_threshold_inr")
        or yaml_data.get("DEFAULT_APPROVAL_THRESHOLD_INR"),
        default=3000.0
    )
    default_max_item_quantity = _parse_int(
        os.getenv("DEFAULT_MAX_ITEM_QUANTITY")
        or guardrails_cfg.get("max_item_quantity")
        or guardrails_cfg.get("default_max_item_quantity")
        or yaml_data.get("DEFAULT_MAX_ITEM_QUANTITY"),
        default=5
    )
    allowed_currency = (
        os.getenv("ALLOWED_CURRENCY")
        or guardrails_cfg.get("allowed_currency")
        or yaml_data.get("ALLOWED_CURRENCY")
        or "INR"
    )
    allowed_categories = (
        guardrails_cfg.get("allowed_categories")
        or yaml_data.get("ALLOWED_CATEGORIES")
        or [
            "smartphones",
            "mobile_accessories",
            "mechanical_keyboards",
            "computer_peripherals",
            "workspace_accessories",
            "developer_gear",
            "ergonomics",
            "audio_equipment",
            "nutrition_and_fitness",
            "running_shoes",
            "health_and_groceries"
        ]
    )

    # 6. Merchant settings
    merchant_id = (
        os.getenv("MERCHANT_ID")
        or merchant_cfg.get("merchant_id")
        or yaml_data.get("MERCHANT_ID")
        or "merch_pay_pipeline_01"
    )
    merchant_name = (
        os.getenv("MERCHANT_NAME")
        or merchant_cfg.get("merchant_name")
        or yaml_data.get("MERCHANT_NAME")
        or "pay-pipeline Store"
    )

    # 7. Discount settings
    discount_tier_1_threshold = _parse_float(
        os.getenv("DISCOUNT_TIER_1_THRESHOLD")
        or discount_cfg.get("tier_1_threshold_inr")
        or discount_cfg.get("default_tier_1_threshold_inr")
        or yaml_data.get("DISCOUNT_TIER_1_THRESHOLD"),
        default=3000.0
    )
    discount_tier_1_rate = _parse_float(
        os.getenv("DISCOUNT_TIER_1_RATE")
        or discount_cfg.get("tier_1_rate")
        or yaml_data.get("DISCOUNT_TIER_1_RATE"),
        default=0.10
    )
    discount_tier_1_max_cap = _parse_float(
        os.getenv("DISCOUNT_TIER_1_MAX_CAP")
        or discount_cfg.get("tier_1_max_cap_inr")
        or yaml_data.get("DISCOUNT_TIER_1_MAX_CAP"),
        default=500.0
    )
    discount_bundle_discount_rate = _parse_float(
        os.getenv("DISCOUNT_BUNDLE_DISCOUNT_RATE")
        or discount_cfg.get("bundle_discount_rate")
        or yaml_data.get("DISCOUNT_BUNDLE_DISCOUNT_RATE"),
        default=0.05
    )
    discount_promo_codes = (
        discount_cfg.get("promo_codes")
        or yaml_data.get("DISCOUNT_PROMO_CODES")
        or {
            "GROWTH10": {"rate": 0.10, "max_discount": 500.0, "min_subtotal": 2000.0},
            "SAVE15": {"rate": 0.15, "max_discount": 750.0, "min_subtotal": 4000.0},
        }
    )

    # 8. Payment Links Customer defaults
    payment_customer_name = (
        os.getenv("PAYMENT_CUSTOMER_NAME")
        or payment_cfg.get("customer_name")
        or yaml_data.get("PAYMENT_CUSTOMER_NAME")
        or "pay-pipeline Buyer"
    )
    payment_customer_contact = (
        os.getenv("PAYMENT_CUSTOMER_CONTACT")
        or payment_cfg.get("customer_contact")
        or yaml_data.get("PAYMENT_CUSTOMER_CONTACT")
        or "+919999999999"
    )
    payment_customer_email = (
        os.getenv("PAYMENT_CUSTOMER_EMAIL")
        or payment_cfg.get("customer_email")
        or yaml_data.get("PAYMENT_CUSTOMER_EMAIL")
        or "buyer@pay-pipeline.com"
    )

    # 9. ACP Quote Expiration
    acp_quote_expiration = _parse_int(
        os.getenv("ACP_QUOTE_EXPIRATION_SECONDS")
        or guardrails_cfg.get("quote_expiration_seconds")
        or yaml_data.get("ACP_QUOTE_EXPIRATION_SECONDS"),
        default=300
    )

    # 10. Merchant Baseline AOV
    merchant_baseline_aov = _parse_float(
        os.getenv("MERCHANT_BASELINE_AOV_INR")
        or merchant_cfg.get("baseline_aov_inr")
        or yaml_data.get("MERCHANT_BASELINE_AOV_INR"),
        default=3000.0
    )

    return Settings(
        PROJECT_NAME=project_name,
        API_V1_STR=api_v1_str,
        PORT=port,
        HOST=host,
        DATABASE_URL=db_url,
        PAYMENT_PROVIDER_MODE=payment_provider_mode,
        RAZORPAY_KEY_ID=razorpay_key_id,
        RAZORPAY_KEY_SECRET=razorpay_key_secret,
        RAZORPAY_WEBHOOK_SECRET=razorpay_webhook_secret,
        AUDIT_HMAC_SECRET=audit_hmac_secret,
        LLM_PROVIDER=llm_provider,
        GROQ_API_KEY=groq_api_key,
        GROQ_MODEL=groq_model,
        GROQ_MAX_TOOL_ROUNDS=groq_max_tool_rounds,
        ENABLE_GROQ_BROWSER_SEARCH=enable_groq_browser_search,
        SEARCH_PROVIDER=search_provider,
        TAVILY_API_KEY=tavily_api_key,
        MAX_SEARCH_RESULTS=max_search_results,
        DEFAULT_MAX_TXN_AMOUNT_INR=default_max_txn,
        DEFAULT_MAX_CUMULATIVE_SPEND_INR=default_max_cumulative,
        DEFAULT_APPROVAL_THRESHOLD_INR=default_approval_threshold,
        DEFAULT_MAX_ITEM_QUANTITY=default_max_item_quantity,
        ALLOWED_CURRENCY=allowed_currency,
        ALLOWED_CATEGORIES=allowed_categories,
        MERCHANT_ID=merchant_id,
        MERCHANT_NAME=merchant_name,
        CONFIG_FILE_PATH=str(cfg_file) if cfg_file else None,
        CATALOG_DB_PATH=catalog_db_path,
        DISCOUNT_TIER_1_THRESHOLD=discount_tier_1_threshold,
        DISCOUNT_TIER_1_RATE=discount_tier_1_rate,
        DISCOUNT_TIER_1_MAX_CAP=discount_tier_1_max_cap,
        DISCOUNT_BUNDLE_DISCOUNT_RATE=discount_bundle_discount_rate,
        DISCOUNT_PROMO_CODES=discount_promo_codes,
        PAYMENT_CUSTOMER_NAME=payment_customer_name,
        PAYMENT_CUSTOMER_CONTACT=payment_customer_contact,
        PAYMENT_CUSTOMER_EMAIL=payment_customer_email,
        ACP_QUOTE_EXPIRATION_SECONDS=acp_quote_expiration,
        MERCHANT_BASELINE_AOV_INR=merchant_baseline_aov,
    )


settings = load_settings()
