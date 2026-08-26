from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.app.tools.money_tools import money_tools
from backend.app.database.repositories import cart_repo

router = APIRouter(prefix="/checkout", tags=["Direct Checkout"])


class CheckoutRequest(BaseModel):
    cart_id: str
    user_id: str = "user_default_buyer"
    idempotency_key: Optional[str] = None
    approval_token: Optional[str] = None


@router.post("")
def execute_checkout(req: CheckoutRequest):
    """Execute direct server-side checkout on a cart passing through deterministic guardrails."""
    cart = cart_repo.get_cart(req.cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail=f"Cart '{req.cart_id}' not found.")

    res = money_tools.create_order_guarded(
        cart=cart,
        user_id=req.user_id,
        idempotency_key=req.idempotency_key,
        approval_token=req.approval_token
    )
    return res
