import pytest, json, hmac, hashlib
from backend.app.payment.webhook_handler import webhook_handler
from backend.app.config import settings

def test_authoritative_webhook_verification():
    payload_dict = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_webhook_123",
                    "order_id": "order_test_webhook_123",
                    "amount": 449900,
                    "currency": "INR",
                    "status": "captured"
                }
            }
        }
    }
    raw_payload = json.dumps(payload_dict)
    
    # Generate valid HMAC signature
    valid_sig = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        raw_payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    # 1. Test Valid Signature
    success, code, data = webhook_handler.handle_webhook(raw_payload, valid_sig)
    assert success
    assert code == "PAYMENT_CAPTURED_VERIFIED"
    assert data["payment_id"] == "pay_test_webhook_123"

    # 2. Test Invalid/Spoofed Signature
    invalid_sig = "fake_signature_spoof_attempt_99999"
    success_spoof, code_spoof, _ = webhook_handler.handle_webhook(raw_payload, invalid_sig)
    assert not success_spoof
    assert code_spoof == "INVALID_WEBHOOK_SIGNATURE"
