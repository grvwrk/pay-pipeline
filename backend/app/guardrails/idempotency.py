from typing import Dict, Optional, Any
import datetime

class IdempotencyManager:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def check_key(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        if not idempotency_key:
            return None
        return self._cache.get(idempotency_key)

    def register_key(self, idempotency_key: str, result: Dict[str, Any]):
        if idempotency_key:
            self._cache[idempotency_key] = {
                "result": result,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }

    def clear(self):
        self._cache.clear()

idempotency_manager = IdempotencyManager()
