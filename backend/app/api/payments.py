from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from backend.app.config import settings
from backend.app.tools.money_tools import money_tools
from backend.app.database.repositories import payment_repo


router = APIRouter(prefix="/payments", tags=["Payment initiation"])


@router.get("/checkout-config")
def checkout_config():
    """Public client configuration; the Razorpay secret is never exposed."""
    return {
        "provider_mode": settings.PAYMENT_PROVIDER_MODE,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID if settings.PAYMENT_PROVIDER_MODE == "razorpay" else None,
    }


@router.get("/{payment_id}")
def get_payment(payment_id: str):
    """Retrieve full payment details and verification status."""
    payment = payment_repo.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment '{payment_id}' not found.")
    return payment


class PaymentInitiationRequest(BaseModel):
    order_id: str
    amount_inr: float = Field(gt=0)
    method: str = "upi"
    simulate_failure: bool = False
    user_id: str = "user_default_buyer"


@router.post("/initiate")
def initiate_payment(request: PaymentInitiationRequest):
    """Initiate a local test payment; final success always requires an authoritative webhook."""
    if settings.PAYMENT_PROVIDER_MODE != "simulator":
        raise HTTPException(status_code=501, detail="Configure a Razorpay provider adapter for live payment initiation.")
    try:
        return money_tools.capture_payment_guarded(
            order_id=request.order_id,
            amount_inr=request.amount_inr,
            method=request.method,
            force_fail=request.simulate_failure,
            user_id=request.user_id
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
