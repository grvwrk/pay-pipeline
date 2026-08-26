import os
import secrets
from pydantic import BaseModel
from typing import Optional, List

class Settings(BaseModel):
    PROJECT_NAME: str = "AeroPay - Agentic Commerce & Revenue Growth Engine"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # Credentials are never embedded in source. The default gateway is an
    # explicitly local simulator; real test-mode integration requires env vars.
    PAYMENT_PROVIDER_MODE: str = os.getenv("PAYMENT_PROVIDER_MODE", "simulator")
    RAZORPAY_KEY_ID: Optional[str] = os.getenv("RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET: Optional[str] = os.getenv("RAZORPAY_KEY_SECRET")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET") or secrets.token_urlsafe(32)
    
    # Cryptographic Audit Secret
    AUDIT_HMAC_SECRET: str = os.getenv("AUDIT_HMAC_SECRET") or secrets.token_urlsafe(32)
    
    # Deterministic Guardrail Defaults
    DEFAULT_MAX_TXN_AMOUNT_INR: float = 5000.0      # Hard ceiling per single transaction
    DEFAULT_MAX_CUMULATIVE_SPEND_INR: float = 15000.0 # Cumulative session ceiling
    DEFAULT_APPROVAL_THRESHOLD_INR: float = 3000.0   # Orders > ₹3,000 require gated human confirmation
    DEFAULT_MAX_ITEM_QUANTITY: int = 5
    ALLOWED_CURRENCY: str = "INR"
    ALLOWED_CATEGORIES: List[str] = [
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
    MERCHANT_ID: str = "merch_aeropay_electronics_01"
    MERCHANT_NAME: str = "AeroNation Tech & Lifestyle Store"

settings = Settings()
