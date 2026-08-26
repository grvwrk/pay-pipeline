from typing import Dict
from backend.app.config import settings

class SpendLimiter:
    def __init__(self):
        self.user_cumulative_spend: Dict[str, float] = {}

    def get_user_cumulative_spend(self, user_id: str) -> float:
        return self.user_cumulative_spend.get(user_id, 0.0)

    def record_spend(self, user_id: str, amount: float):
        self.user_cumulative_spend[user_id] = self.get_user_cumulative_spend(user_id) + amount

    def reset_user_spend(self, user_id: str):
        self.user_cumulative_spend[user_id] = 0.0

spend_limiter = SpendLimiter()
