import os
from pydantic import BaseModel
from typing import Optional, List

class Settings(BaseModel):
    PROJECT_NAME: str = "AeroPay - Agentic Commerce & Revenue Growth Engine"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # Razorpay Test Credentials
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_aeropay_demo_key")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "rzp_test_secret_aeropay_2026")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "whsec_aeropay_webhook_secret_9988")
    
    # Cryptographic Audit Secret
    AUDIT_HMAC_SECRET: str = os.getenv("AUDIT_HMAC_SECRET", "aeropay_cryptographic_audit_signing_key_402")
    
    # Deterministic Guardrail Defaults
    DEFAULT_MAX_TXN_AMOUNT_INR: float = 60000.0   # Default transaction ceiling (supports smartphones & high-end workstations)
    DEFAULT_MAX_CUMULATIVE_SPEND_INR: float = 150000.0
    DEFAULT_APPROVAL_THRESHOLD_INR: float = 30000.0  # Orders > ₹30,000 require human-in-the-loop confirmation
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
        "audio_equipment"
    ]
    MERCHANT_ID: str = "merch_aeropay_electronics_01"
    MERCHANT_NAME: str = "AeroNation Tech & Lifestyle Store"

settings = Settings()
