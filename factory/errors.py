class ValidationError(Exception):
    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(f"Validation error on '{field}': {message}")


class CollisionError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Company '{name}' already exists in companies/")


class BudgetExceeded(Exception):
    def __init__(self, spent: int, limit: int) -> None:
        super().__init__(f"Token budget exceeded: {spent} > {limit}")


class RiskBlocked(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Action blocked by risk gate: {reason}")
