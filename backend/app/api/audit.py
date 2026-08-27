from fastapi import APIRouter, HTTPException, status
from backend.app.database.repositories import audit_repo

router = APIRouter(prefix="/audit", tags=["Audit & Verification"])


@router.get("/chain")
def get_audit_chain():
    """Retrieve complete tamper-evident audit ledger."""
    chain = audit_repo.list_all()
    if not chain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit ledger is empty. No audit events recorded yet."
        )
    return {"total_events": len(chain), "chain": chain}


@router.get("/verify")
def verify_audit_integrity():
    """Verify cryptographic hash integrity of the entire audit chain."""
    chain = audit_repo.list_all()
    if not chain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cannot verify integrity: Audit ledger is empty."
        )
    
    is_valid, bad_event_id = audit_repo.verify_chain_integrity()
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cryptographic integrity check failed at event ID: {bad_event_id}"
        )
    
    return {"status": "VERIFIED", "message": "All cryptographic signatures in audit ledger are valid."}


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