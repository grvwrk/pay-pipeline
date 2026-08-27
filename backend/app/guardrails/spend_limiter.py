from typing import Optional
from sqlalchemy.orm import Session
from backend.app.database.repositories import spend_repo


class SpendLimiter:
    def __init__(self, max_cumulative_limit_inr: float = 100000.0):
        self.max_cumulative_limit_inr = max_cumulative_limit_inr

    def get_user_cumulative_spend(self, user_id: str, db: Optional[Session] = None) -> float:
        return spend_repo.get_user_cumulative_spend(user_id, db=db)

    def is_spend_allowed(self, user_id: str, proposed_amount: float, db: Optional[Session] = None) -> bool:
        current_spend = self.get_user_cumulative_spend(user_id, db=db)
        return (current_spend + proposed_amount) <= self.max_cumulative_limit_inr

    def record_spend(self, user_id: str, amount: float, db: Optional[Session] = None):
        spend_repo.record_spend(user_id, amount, db=db)

    def reset_spend(self, user_id: str, db: Optional[Session] = None):
        spend_repo.reset_spend(user_id, db=db)

spend_limiter = SpendLimiter()
