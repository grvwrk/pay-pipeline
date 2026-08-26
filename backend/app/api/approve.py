from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.app.guardrails.policy_engine import policy_engine

router = APIRouter(prefix="/approve", tags=["Human Approval"])


class ApprovalRequest(BaseModel):
    approval_token: str


@router.post("")
def approve_transaction(req: ApprovalRequest):
    """Explicitly register human 2FA approval for a gated transaction exceeding the automatic threshold."""
    if not req.approval_token:
        raise HTTPException(status_code=400, detail="Approval token must be provided.")

    policy_engine.register_human_approval(req.approval_token)
    return {
        "status": "APPROVED",
        "approval_token": req.approval_token,
        "message": "Human approval token verified and registered. Gated money tools unlocked for this transaction."
    }
