import pytest
from backend.app.audit.audit_service import AuditService
from backend.app.database.db import init_db


def test_cryptographic_hash_chain_integrity():
    audit = AuditService()
    initial_count = len(audit.get_all_records())

    # Record multiple events
    audit.record_event(
        actor_id="user_1",
        actor_role="USER",
        action="CATALOG_SEARCH",
        arguments={"query": "keyboard"},
        guardrail_decision="APPROVED"
    )
    audit.record_event(
        actor_id="user_1",
        actor_role="CHECKOUT_AGENT",
        action="CREATE_ORDER",
        arguments={"amount": 4499.0, "order_id": "order_123"},
        guardrail_decision="APPROVED"
    )

    # Verify untampered chain
    verification = audit.verify_chain_integrity()
    assert verification.is_valid
    assert verification.total_records == initial_count + 2
    assert verification.tampered_index is None


def test_cryptographic_tamper_detection():
    audit = AuditService()

    rec = audit.record_event(
        actor_id="user_1",
        actor_role="CHECKOUT_AGENT",
        action="CREATE_ORDER",
        arguments={"amount": 4499.0, "order_id": "order_123"},
        guardrail_decision="APPROVED"
    )

    # Tamper with the log entry
    audit.tamper_simulation(target_index=rec.index, fake_amount=100.0)

    try:
        # Verify detection
        verification = audit.verify_chain_integrity()
        assert not verification.is_valid
        assert verification.tampered_index == rec.index
        assert "mismatch" in verification.error_detail.lower() or "alteration" in verification.error_detail.lower()
    finally:
        # Restore original arguments so subsequent tests have a valid chain
        audit.restore_record(target_index=rec.index, original_arguments=rec.arguments)
