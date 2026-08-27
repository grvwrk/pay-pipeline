import hashlib
import json
from typing import Any, Dict


def compute_record_hash(
    prev_hash: str,
    index: int,
    timestamp: str,
    actor_id: str,
    actor_role: str,
    action: str,
    intent: str,
    arguments: Dict[str, Any],
    guardrail_decision: str,
    transaction_state: str,
    result_status: str
) -> str:
    """Computes an immutable SHA-256 hash over all canonical record state fields."""
    payload = {
        "prev_hash": prev_hash,
        "index": index,
        "timestamp": timestamp,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "action": action,
        "intent": intent or "",
        "arguments": arguments or {},
        "guardrail_decision": guardrail_decision or "",
        "transaction_state": transaction_state or "",
        "result_status": result_status or ""
    }
    canonical_repr = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()