from fastapi import APIRouter, Request, Header, HTTPException
from backend.app.payment.webhook_handler import webhook_handler

router = APIRouter(prefix="/webhooks", tags=["Razorpay Webhooks"])

@router.post("/razorpay")
async def receive_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None)
):
    """Authoritative Razorpay webhook receiver with cryptographic HMAC validation."""
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")
    
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header")

    success, code, data = webhook_handler.handle_webhook(body_str, x_razorpay_signature)
    if not success:
        raise HTTPException(status_code=400, detail=code)

    return {"status": "ACKNOWLEDGED", "code": code, "data": data}
