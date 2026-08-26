import hashlib, json

def compute_record_hash(prev_hash: str, index: int, timestamp: str, actor_id: str, action: str, data: dict) -> str:
    canonical_repr = f"{prev_hash}|{index}|{timestamp}|{actor_id}|{action}|{json.dumps(data, sort_keys=True)}"
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()
