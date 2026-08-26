from fastapi import APIRouter, HTTPException
from typing import List, Optional
from backend.app.models.order import RazorpayOrder
from backend.app.database.repositories import order_repo

router = APIRouter(prefix="/orders", tags=["Order Management"])


@router.get("", response_model=List[RazorpayOrder])
def list_orders(limit: int = 50):
    """List recent commerce orders."""
    return order_repo.list_orders(limit=limit)


@router.get("/{order_id}", response_model=RazorpayOrder)
def get_order(order_id: str):
    """Retrieve full order details and current transaction state."""
    order = order_repo.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order '{order_id}' not found.")
    return order
