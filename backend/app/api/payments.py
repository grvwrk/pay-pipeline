from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.tools.money_tools import money_tools


router = APIRouter(prefix="/payments", tags=["Payment initiation"])


class PaymentInitiationRequest(BaseModel):
    order_id: str
    amount_inr: float = Field(gt=0)
    method: str = "upi"
    simulate_failure: bool = False


@router.post("/initiate")
def initiate_payment(request: PaymentInitiationRequest):
    """Initiate a local test payment; final success always requires a webhook."""
    if settings.PAYMENT_PROVIDER_MODE != "simulator":
        raise HTTPException(status_code=501, detail="Configure a Razorpay provider adapter for live payment initiation.")
    try:
        return money_tools.capture_payment_guarded(
            order_id=request.order_id,
            amount_inr=request.amount_inr,
            method=request.method,
            force_fail=request.simulate_failure,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
