import os

def write(filepath, content):
    d = os.path.dirname(filepath)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Wrote: {filepath}")

write('backend/app/audit/signer.py', '''import hmac, hashlib, json
from backend.app.config import settings

def sign_data(data: dict, secret: str = settings.AUDIT_HMAC_SECRET) -> str:
    canonical_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), canonical_bytes, hashlib.sha256).hexdigest()

def verify_signature(data: dict, signature: str, secret: str = settings.AUDIT_HMAC_SECRET) -> bool:
    expected = sign_data(data, secret)
    return hmac.compare_digest(expected, signature)
''')

write('backend/app/audit/hash_chain.py', '''import hashlib, json

def compute_record_hash(prev_hash: str, index: int, timestamp: str, actor_id: str, action: str, data: dict) -> str:
    canonical_repr = f"{prev_hash}|{index}|{timestamp}|{actor_id}|{action}|{json.dumps(data, sort_keys=True)}"
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()
''')

write('backend/app/audit/audit_service.py', '''import uuid, datetime
from typing import List, Optional, Dict, Any
from backend.app.models.audit import AuditRecord, AuditChainVerificationResult, ExplainabilityReport
from backend.app.audit.signer import sign_data, verify_signature
from backend.app.audit.hash_chain import compute_record_hash

class AuditService:
    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self):
        self.chain: List[AuditRecord] = []
        self._init_genesis()

    def _init_genesis(self):
        genesis_data = {"system": "AeroPay Cryptographic Audit Engine", "standard": "HMAC-SHA256 Hash Chain"}
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"
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
            arguments=genesis_data,
            guardrail_decision="APPROVED",
            result_status="SUCCESS",
            signature=sig,
            explainability_notes="Genesis block initializing immutable cryptographic ledger for AeroPay."
        )
        self.chain.append(genesis_record)

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
        explainability_notes: str = ""
    ) -> AuditRecord:
        prev_record = self.chain[-1]
        new_index = prev_record.index + 1
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        
        record_hash = compute_record_hash(
            prev_record.record_hash,
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
            prev_hash=prev_record.record_hash,
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
            explainability_notes=explainability_notes
        )
        self.chain.append(record)
        return record

    def get_all_records(self) -> List[AuditRecord]:
        return list(reversed(self.chain))

    def verify_chain_integrity(self) -> AuditChainVerificationResult:
        if not self.chain:
            return AuditChainVerificationResult(
                is_valid=False,
                total_records=0,
                genesis_hash=self.GENESIS_HASH,
                latest_hash=self.GENESIS_HASH,
                error_detail="Audit chain is empty."
            )

        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]

            if curr.prev_hash != prev.record_hash:
                return AuditChainVerificationResult(
                    is_valid=False,
                    total_records=len(self.chain),
                    genesis_hash=self.chain[0].record_hash,
                    latest_hash=self.chain[-1].record_hash,
                    tampered_index=curr.index,
                    error_detail=f"Hash chain link broken at record #{curr.index}. Expected prev_hash {prev.record_hash[:12]}..., found {curr.prev_hash[:12]}..."
                )

            expected_hash = compute_record_hash(
                curr.prev_hash,
                curr.index,
                curr.timestamp,
                curr.actor_id,
                curr.action,
                curr.arguments
            )
            if expected_hash != curr.record_hash:
                return AuditChainVerificationResult(
                    is_valid=False,
                    total_records=len(self.chain),
                    genesis_hash=self.chain[0].record_hash,
                    latest_hash=self.chain[-1].record_hash,
                    tampered_index=curr.index,
                    error_detail=f"Content alteration detected at record #{curr.index}. Cryptographic hash mismatch."
                )

            sig_payload = {
                "index": curr.index,
                "hash": curr.record_hash,
                "actor": curr.actor_id,
                "action": curr.action,
                "arguments": curr.arguments,
                "guardrail_decision": curr.guardrail_decision
            }
            if not verify_signature(sig_payload, curr.signature):
                return AuditChainVerificationResult(
                    is_valid=False,
                    total_records=len(self.chain),
                    genesis_hash=self.chain[0].record_hash,
                    latest_hash=self.chain[-1].record_hash,
                    tampered_index=curr.index,
                    error_detail=f"HMAC digital signature invalid at record #{curr.index}."
                )

        return AuditChainVerificationResult(
            is_valid=True,
            total_records=len(self.chain),
            genesis_hash=self.chain[0].record_hash,
            latest_hash=self.chain[-1].record_hash,
            tampered_index=None,
            error_detail=None
        )

    def tamper_simulation(self, target_index: int, fake_amount: float) -> bool:
        for record in self.chain:
            if record.index == target_index:
                record.arguments["amount"] = fake_amount
                record.arguments["tampered"] = True
                return True
        return False

audit_service = AuditService()
''')

print("Audit service written successfully!")
