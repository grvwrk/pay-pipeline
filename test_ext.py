import os

def write(filepath, content):
    d = os.path.dirname(filepath)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Wrote: {filepath}")

write('tests/test_workflow.py', '''import pytest
import asyncio
from backend.app.workflows.commerce_workflow import commerce_workflow

@pytest.mark.anyio
async def test_workflow_catalog_discovery():
    res = await commerce_workflow.run(
        user_message="Show me mechanical keyboards under 5000",
        user_id="test_buyer_01"
    )
    assert res["type"] == "CATALOG_DISCOVERY"
    assert len(res["products"]) >= 1
    assert "Keychron" in res["message"] or "Royal Kludge" in res["message"] or "Ducky" in res["message"]
    assert res["upsell_bundle"] is not None

@pytest.mark.anyio
async def test_workflow_guardrail_denial():
    # Attempting to buy 7999 keyboard with 5000 limit
    res = await commerce_workflow.run(
        user_message="Buy me the AeroPro CNC Anodized Aluminium Gasket Keyboard for 7999",
        user_id="test_buyer_01"
    )
    assert res["type"] == "GUARDRAIL_DENIED"
    assert res["decision_code"] == "DENIED_SPEND_LIMIT"
    assert "exceeds" in res["message"]
''')

write('tests/test_webhooks.py', '''import pytest, json, hmac, hashlib
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
''')

print("Extended test suite written!")
