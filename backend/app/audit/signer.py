import hmac, hashlib, json
from backend.app.config import settings

def sign_data(data: dict, secret: str = settings.AUDIT_HMAC_SECRET) -> str:
    canonical_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), canonical_bytes, hashlib.sha256).hexdigest()

def verify_signature(data: dict, signature: str, secret: str = settings.AUDIT_HMAC_SECRET) -> bool:
    expected = sign_data(data, secret)
    return hmac.compare_digest(expected, signature)
