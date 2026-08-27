import hmac
import hashlib
import json
from typing import Dict, Any, Optional
from backend.app.config import settings


def _get_secret(secret: Optional[str] = None) -> str:
    key = secret or settings.AUDIT_HMAC_SECRET or settings.RAZORPAY_KEY_SECRET or "fallback_audit_hmac_secret_key"
    return str(key)


def sign_data(data: Dict[str, Any], secret: Optional[str] = None) -> str:
    """Signs canonical dictionary data using HMAC-SHA256."""
    key = _get_secret(secret)
    canonical_bytes = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hmac.new(key.encode("utf-8"), canonical_bytes, hashlib.sha256).hexdigest()


def verify_signature(data: Dict[str, Any], signature: str, secret: Optional[str] = None) -> bool:
    """Verifies HMAC-SHA256 signature against data payload."""
    if not signature:
        return False
    expected = sign_data(data, secret)
    return hmac.compare_digest(expected, signature)