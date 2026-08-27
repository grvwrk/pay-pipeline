from fastapi import APIRouter, HTTPException, status
from backend.app.database.repositories import audit_repo
from backend.app.audit.audit_service import audit_service

router = APIRouter(prefix="/audit", tags=["Audit & Verification"])


@router.get("/chain")
def get_audit_chain():
    """Retrieve complete tamper-evident audit ledger."""
    chain = audit_service.get_all_records()
    if not chain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit ledger is empty. No audit events recorded yet."
        )
    return {"total_events": len(chain), "chain": chain}


@router.get("/verify")
def verify_audit_integrity():
    """Verify cryptographic hash integrity of the entire audit chain."""
    chain = audit_service.get_all_records()
    if not chain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cannot verify integrity: Audit ledger is empty."
        )
    
    verification = audit_service.verify_chain_integrity()
    if not verification.is_valid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cryptographic integrity check failed at index: {verification.tampered_index}. Detail: {verification.error_detail}"
        )
    
    return {"status": "VERIFIED", "message": "All cryptographic signatures in audit ledger are valid.", "is_valid": True}


@router.get("/{transaction_id}")
def get_audit_record(transaction_id: str):
    """Retrieve audit record by transaction ID."""
    record = audit_repo.get_by_transaction_id(transaction_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No audit record found for transaction ID '{transaction_id}'."
        )
    return record