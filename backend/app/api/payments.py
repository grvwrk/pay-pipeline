from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from backend.app.config import settings
from backend.app.tools.money_tools import money_tools
from backend.app.database.repositories import payment_repo, order_repo

router = APIRouter(prefix="/payments", tags=["Payment Integration"])


@router.get("/checkout-config")
def get_checkout_config():
    """Get active payment gateway client parameters."""
    key_id = getattr(settings, "RAZORPAY_KEY_ID", None)
    if not key_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Razorpay key ID is not configured in application settings."
        )
    return {"key_id": key_id, "currency": "INR"}

@router.get("/{payment_id}")
def get_payment_details(payment_id: str):
    """Retrieve payment and order association by payment_id or order_id."""
    order = order_repo.get_by_id(payment_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment record or Order ID '{payment_id}' not found."
        )
    return {
        "order_id": order.order_id,
        "amount": order.amount,
        "currency": getattr(order, "currency", "INR"),
        "state": order.state,
        "created_at": order.created_at
    }


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
