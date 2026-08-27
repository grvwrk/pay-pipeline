from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from backend.app.tools.money_tools import money_tools
from backend.app.database.repositories import refund_repo

router = APIRouter(prefix="/refund", tags=["Refund Operations"])


class RefundRequest(BaseModel):
    payment_id: str
    amount_inr: float = Field(gt=0, description="Amount to refund in INR")
    user_id: str = Field(..., description="ID of the user requesting the refund")
    reason: str = "Customer request"


@router.post("")
def execute_refund(req: RefundRequest):
    """
    Process refund bounded by original payment amount.
    Fails deterministically if refund exceeds remaining paid balance or if payment wasn't captured.
    """
    res = money_tools.issue_refund_guarded(
        payment_id=req.payment_id,
        amount_inr=req.amount_inr,
        user_id=req.user_id,
        reason=req.reason
    )
    if not isinstance(res, dict) or not res.get("success"):
        error_msg = res.get("error", "Refund request denied by policy.") if isinstance(res, dict) else "Refund process failed."
        raise HTTPException(status_code=400, detail=error_msg)
    return res


@router.get("/{refund_id}")
def get_refund(refund_id: str):
    """Retrieve refund details by refund ID."""
    refund = refund_repo.get_refund(refund_id)
    if not refund:
        raise HTTPException(status_code=404, detail=f"Refund '{refund_id}' not found.")
    return refund