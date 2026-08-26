import uuid
import datetime
from typing import List, Optional, Dict, Any
from backend.app.models.audit import AuditRecord, AuditChainVerificationResult, ExplainabilityReport
from backend.app.audit.signer import sign_data, verify_signature
from backend.app.audit.hash_chain import compute_record_hash
from backend.app.database.repositories import audit_repo
from backend.app.database.db import SessionLocal
from backend.app.database.models import AuditRecordModel
import json


class AuditService:
    """
    Tamper-Evident SHA-256 Hash-Chained Cryptographic Audit Ledger.
    Every event is chained, signed with HMAC-SHA256, and persisted into SQLite.
    """

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self):
        self._ensure_genesis()

    def _ensure_genesis(self):
        latest = audit_repo.get_latest()
        if not latest:
            genesis_data = {
                "system": "pay-pipeline Cryptographic Audit Engine",
                "standard": "HMAC-SHA256 Hash Chain",
                "version": "1.0.0"
            }
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            record_hash = compute_record_hash(self.GENESIS_HASH, 0, timestamp, "SYSTEM", "GENESIS_INITIALIZATION", genesis_data)
            sig = sign_data({"index": 0, "hash": record_hash, "data": genesis_data})
            genesis_record = AuditRecord(
                index=0,
                timestamp=timestamp,
                event_id="evt_genesis_0000",
                prev_hash=self.GENESIS_HASH,
                record_hash=record_hash,
                actor_id="SYSTEM",
                actor_role="AUDIT_ENGINE",
                action="GENESIS_INITIALIZATION",
                intent="SYSTEM_BOOT",
                tool_name=None,
                arguments=genesis_data,
                guardrail_decision="APPROVED",
                approval_required=False,
                transaction_state="INITIALIZED",
                result_status="SUCCESS",
                signature=sig,
                explainability_notes="Genesis block initializing immutable cryptographic ledger for pay-pipeline."
            )
            audit_repo.save_record(genesis_record)

    def record_event(
        self,
        actor_id: str,
        actor_role: str,
        action: str,
        arguments: Dict[str, Any],
        intent: Optional[str] = None,
        tool_name: Optional[str] = None,
        guardrail_decision: Optional[str] = None,
        approval_required: bool = False,
        transaction_state: Optional[str] = None,
        result_status: str = "SUCCESS",
        latency_ms: float = 0.0,
        explainability_notes: str = ""
    ) -> AuditRecord:
        latest = audit_repo.get_latest()
        if not latest:
            self._ensure_genesis()
            latest = audit_repo.get_latest()

        new_index = (latest.index + 1) if latest else 0
        prev_hash = latest.record_hash if latest else self.GENESIS_HASH
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        event_id = f"evt_{uuid.uuid4().hex[:12]}"

        record_hash = compute_record_hash(
            prev_hash,
            new_index,
            timestamp,
            actor_id,
            action,
            arguments
        )

        sig = sign_data({
            "index": new_index,
            "hash": record_hash,
            "actor": actor_id,
            "action": action,
            "arguments": arguments,
            "guardrail_decision": guardrail_decision
        })

        record = AuditRecord(
            index=new_index,
            timestamp=timestamp,
            event_id=event_id,
            prev_hash=prev_hash,
            record_hash=record_hash,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            intent=intent,
            tool_name=tool_name,
            arguments=arguments,
            guardrail_decision=guardrail_decision,
            approval_required=approval_required,
            transaction_state=transaction_state,
            result_status=result_status,
            signature=sig,
            latency_ms=latency_ms,
            explainability_notes=explainability_notes
        )
        audit_repo.save_record(record)
        return record

    def get_all_records(self) -> List[AuditRecord]:
        return list(reversed(audit_repo.get_all()))

    def tamper_simulation(self, target_index: int, fake_amount: float):
        """Simulate a database attack by altering the recorded arguments in SQLite."""
        with SessionLocal() as db:
            m = db.query(AuditRecordModel).filter(AuditRecordModel.index == target_index).first()
            if m:
                args = json.loads(m.arguments_json or "{}")
                args["amount"] = fake_amount
                args["tampered"] = True
                m.arguments_json = json.dumps(args)
                db.commit()

    def restore_record(self, target_index: int, original_arguments: Dict[str, Any]):
        """Restore original untampered record arguments."""
        with SessionLocal() as db:
            m = db.query(AuditRecordModel).filter(AuditRecordModel.index == target_index).first()
            if m:
                m.arguments_json = json.dumps(original_arguments)
                db.commit()

    def verify_chain_integrity(self) -> AuditChainVerificationResult:
        chain = audit_repo.get_all()
        if not chain:
            return AuditChainVerificationResult(
                is_valid=True,
                total_records=0,
                genesis_hash=self.GENESIS_HASH,
                latest_hash=self.GENESIS_HASH,
                tampered_index=None,
                error_detail=None
            )

        latest_h = chain[-1].record_hash

        for i, record in enumerate(chain):
            if i == 0:
                expected_prev = self.GENESIS_HASH
            else:
                expected_prev = chain[i - 1].record_hash

            if record.prev_hash != expected_prev:
                return AuditChainVerificationResult(
                    is_valid=False,
                    total_records=len(chain),
                    genesis_hash=self.GENESIS_HASH,
                    latest_hash=latest_h,
                    tampered_index=record.index,
                    error_detail=f"Hash chain broken at index {record.index}. prev_hash does not match previous block hash."
                )

            recomputed_hash = compute_record_hash(
                record.prev_hash,
                record.index,
                record.timestamp,
                record.actor_id,
                record.action,
                record.arguments
            )

            if record.record_hash != recomputed_hash:
                return AuditChainVerificationResult(
                    is_valid=False,
                    total_records=len(chain),
                    genesis_hash=self.GENESIS_HASH,
                    latest_hash=latest_h,
                    tampered_index=record.index,
                    error_detail=f"Hash mismatch / data alteration detected at index {record.index} (Event {record.event_id})."
                )

            sig_valid = verify_signature({
                "index": record.index,
                "hash": record.record_hash,
                "actor": record.actor_id,
                "action": record.action,
                "arguments": record.arguments,
                "guardrail_decision": record.guardrail_decision
            }, record.signature)

            if not sig_valid and record.index != 0:
                return AuditChainVerificationResult(
                    is_valid=False,
                    total_records=len(chain),
                    genesis_hash=self.GENESIS_HASH,
                    latest_hash=latest_h,
                    tampered_index=record.index,
                    error_detail=f"Cryptographic signature mismatch at index {record.index}."
                )

        return AuditChainVerificationResult(
            is_valid=True,
            total_records=len(chain),
            genesis_hash=self.GENESIS_HASH,
            latest_hash=latest_h,
            tampered_index=None,
            error_detail=None
        )

    def generate_explainability_report(self, order_id: str) -> Optional[ExplainabilityReport]:
        chain = audit_repo.get_all()
        related_records = []
        for r in chain:
            args = r.arguments or {}
            if args.get("order_id") == order_id or args.get("cart_id") == order_id or r.event_id == order_id:
                related_records.append(r)

        if not related_records:
            return None

        timeline = []
        for r in related_records:
            timeline.append({
                "timestamp": r.timestamp,
                "action": r.action,
                "actor": f"{r.actor_role} ({r.actor_id})",
                "status": r.result_status,
                "decision": r.guardrail_decision,
                "latency_ms": getattr(r, "latency_ms", 0.0),
                "notes": r.explainability_notes
            })

        latest = related_records[-1]
        return ExplainabilityReport(
            order_id=order_id,
            final_status=latest.result_status,
            guardrail_decision=latest.guardrail_decision or "APPROVED",
            policy_reason=latest.explainability_notes,
            timeline=timeline
        )


audit_service = AuditService()
