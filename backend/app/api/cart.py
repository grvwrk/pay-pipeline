import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from backend.app.models.cart import Cart
from backend.app.tools.read_tools import read_tools
from backend.app.database.repositories import cart_repo

router = APIRouter(prefix="/cart", tags=["Shopping Cart Management"])


class CreateCartRequest(BaseModel):
    user_id: str = "user_default_buyer"
    items: List[Dict[str, Any]] = Field(default_factory=list)
    promo_code: Optional[str] = None


class AddItemRequest(BaseModel):
    product_id: str
    quantity: int = Field(default=1, gt=0)


@router.post("", response_model=Cart)
def create_cart(req: CreateCartRequest):
    """Build and price a new shopping cart server-side with automatic discount evaluation."""
    return read_tools.build_cart(user_id=req.user_id, items=req.items, promo_code=req.promo_code)


@router.get("/{cart_id}", response_model=Cart)
def get_cart(cart_id: str):
    """Retrieve an existing shopping cart by cart ID."""
    cart = cart_repo.get_cart(cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail=f"Cart '{cart_id}' not found.")
    return cart


@router.post("/{cart_id}/items", response_model=Cart)
def add_item_to_cart(cart_id: str, req: AddItemRequest):
    """Add a product item to an existing cart and recalculate totals."""
    try:
        return read_tools.add_to_cart(cart_id=cart_id, product_id=req.product_id, quantity=req.quantity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{cart_id}/items/{product_id}", response_model=Cart)
def remove_item_from_cart(cart_id: str, product_id: str):
    """Remove a product item from an existing cart and recalculate totals."""
    try:
        return read_tools.remove_from_cart(cart_id=cart_id, product_id=product_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
