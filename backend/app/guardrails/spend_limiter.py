from backend.app.database.repositories import spend_repo


class SpendLimiter:
    """Tracks cumulative user spend persisted in SQLite."""

    def get_user_cumulative_spend(self, user_id: str) -> float:
        return spend_repo.get_user_cumulative_spend(user_id)

    def record_spend(self, user_id: str, amount: float):
        spend_repo.record_spend(user_id, amount)

    def reset_user_spend(self, user_id: str):
        spend_repo.reset_spend(user_id)


spend_limiter = SpendLimiter()
