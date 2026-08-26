from typing import Optional, Dict, Any
from backend.app.database.repositories import idempotency_repo


class IdempotencyManager:
    """Manages transactional idempotency keys persisted in SQLite."""

    def check_key(self, key: str) -> Optional[Dict[str, Any]]:
        return idempotency_repo.check_key(key)

    def register_key(self, key: str, response_payload: Dict[str, Any]):
        idempotency_repo.register_key(key, response_payload)


idempotency_manager = IdempotencyManager()
