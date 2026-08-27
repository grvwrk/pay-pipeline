from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging

from backend.app.workflows.commerce_workflow import commerce_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Conversational AI Commerce"])

class ChatRequest(BaseModel):
    user_message: Optional[str] = None
    message: Optional[str] = None
    user_id: str = Field(default="user_default_buyer", description="Unique buyer ID")
    approval_token: Optional[str] = None
    idempotency_key: Optional[str] = None
    sku: Optional[str] = None
    force_fail_payment: bool = False

    def get_user_query(self) -> str:
        return (self.user_message or self.message or "").strip()

@router.post("")
async def process_chat(req: ChatRequest) -> Dict[str, Any]:
    query_text = req.get_user_query()
    
    # Fast-fail for empty queries when no explicit approval/SKU action is attached
    if not query_text and not req.approval_token and not req.sku:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request must contain a valid message, approval_token, or sku."
        )

    try:
        # Trigger LlamaIndex Event-Driven Orchestrator
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
        logger.error(f"Workflow execution failed for user {req.user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Commerce workflow failed: {str(e)}"
        )