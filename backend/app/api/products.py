from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from backend.app.models.catalog import Product, ProductFilter
from backend.app.tools.read_tools import read_tools

router = APIRouter(prefix="/products", tags=["Catalog & Products"])


@router.get("", response_model=List[Product])
def list_products(
    query: Optional[str] = Query(None, description="Search keyword"),
    category: Optional[str] = Query(None, description="Category filter"),
    max_price: Optional[float] = Query(None, description="Max INR budget"),
    in_stock_only: bool = Query(True, description="Filter for in-stock items only")
):
    """Retrieve filtered in-stock products from the merchant catalog."""
    return read_tools.search_products(
        query=query,
        category=category,
        max_price=max_price,
        in_stock_only=in_stock_only
    )


@router.get("/{product_id}", response_model=Product)
def get_product(product_id: str):
    """Retrieve full product details, specs, and stock for a given SKU ID."""
    prod = read_tools.get_product(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail=f"Product with SKU '{product_id}' not found.")
    return prod
