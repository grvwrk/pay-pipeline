from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from backend.app.models.audit import AuditRecord, AuditChainVerificationResult, ExplainabilityReport
from backend.app.audit.audit_service import audit_service

router = APIRouter(prefix="/audit", tags=["Cryptographic Audit & Explainability"])

class TamperRequest(BaseModel):
    record_index: int
    altered_amount: float

@router.get("/records", response_model=List[AuditRecord])
def get_audit_records():
    return audit_service.get_all_records()

@router.get("/verify", response_model=AuditChainVerificationResult)
def verify_hash_chain():
    """Live cryptographic verification of the SHA-256 hash chain and HMAC signatures."""
    return audit_service.verify_chain_integrity()

@router.post("/tamper-test")
def simulate_tampering(req: TamperRequest):
    """Demonstrates live tamper detection by intentionally corrupting a log entry."""
    success = audit_service.tamper_simulation(req.record_index, req.altered_amount)
    return {"tampered": success, "message": f"Record #{req.record_index} modified. Run /verify to observe cryptographic detection."}
