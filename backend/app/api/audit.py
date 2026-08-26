from fastapi import APIRouter, HTTPException
from typing import List, Optional
from backend.app.models.audit import AuditRecord, AuditChainVerificationResult, ExplainabilityReport
from backend.app.audit.audit_service import audit_service

router = APIRouter(prefix="/audit", tags=["Cryptographic Audit Ledger"])


@router.get("/chain", response_model=List[AuditRecord])
def get_audit_chain():
    """Retrieve all records in the cryptographic audit trail (latest first)."""
    return audit_service.get_all_records()


@router.get("/verify", response_model=AuditChainVerificationResult)
def verify_audit_chain():
    """Run real-time cryptographic SHA-256 hash-chain and HMAC-SHA256 signature verification."""
    return audit_service.verify_chain_integrity()


@router.get("/explain/{order_id}", response_model=ExplainabilityReport)
def get_explainability_report(order_id: str):
    """Generate human-readable decision timeline and explainability report for an order."""
    report = audit_service.generate_explainability_report(order_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"No audit records found for order/entity '{order_id}'.")
    return report


@router.get("/{transaction_id}")
def get_transaction_audit(transaction_id: str):
    """Retrieve audit history and explainability for a specific transaction/order/payment ID."""
    report = audit_service.generate_explainability_report(transaction_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"No audit trail found for transaction '{transaction_id}'.")
    return report
