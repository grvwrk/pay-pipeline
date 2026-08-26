from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from backend.app.workflows.commerce_workflow import commerce_workflow

router = APIRouter(prefix="/chat", tags=["Conversational AI Commerce"])

class ChatRequest(BaseModel):
    user_message: Optional[str] = None
    message: Optional[str] = None
    user_id: str = "user_default_buyer"
    approval_token: Optional[str] = None
    idempotency_key: Optional[str] = None
    sku: Optional[str] = None
    force_fail_payment: bool = False

    def get_user_query(self) -> str:
        return (self.user_message or self.message or "").strip()

@router.post("")
async def process_chat(req: ChatRequest):
    try:
        query_text = req.get_user_query()
        result = await commerce_workflow.run(
            user_message=query_text,
            user_id=req.user_id,
            approval_token=req.approval_token,
            idempotency_key=req.idempotency_key,
            sku=req.sku,
            force_fail_payment=req.force_fail_payment
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
