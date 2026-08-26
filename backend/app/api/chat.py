from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from backend.app.workflows.commerce_workflow import commerce_workflow

router = APIRouter(prefix="/chat", tags=["Conversational AI Commerce"])

class ChatRequest(BaseModel):
    user_message: str
    user_id: str = "user_default_buyer"
    approval_token: Optional[str] = None
    idempotency_key: Optional[str] = None
    sku: Optional[str] = None
    force_fail_payment: bool = False

@router.post("")
async def process_chat(req: ChatRequest):
    try:
        result = await commerce_workflow.run(
            user_message=req.user_message,
            user_id=req.user_id,
            approval_token=req.approval_token,
            idempotency_key=req.idempotency_key,
            sku=req.sku,
            force_fail_payment=req.force_fail_payment
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
