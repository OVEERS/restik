import time

from fastapi import HTTPException


class FailedLoginLimiter:
    """Считает неудачные попытки входа и блокирует, если их слишком много."""

    def __init__(self, max_failures: int = 5, window_seconds: int = 300):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.failures: dict[str, list[float]] = {}

    def _recent(self, key: str) -> list[float]:
        now = time.monotonic()
        recent = [t for t in self.failures.get(key, []) if now - t < self.window_seconds]
        if recent:
            self.failures[key] = recent
        else:
            # старые записи удаляем, чтобы словарь не рос бесконечно
            self.failures.pop(key, None)
        return recent

    def check(self, key: str) -> None:
        if len(self._recent(key)) >= self.max_failures:
            raise HTTPException(
                status_code=429,
                detail="Слишком много неудачных попыток входа, попробуйте позже",
                headers={"Retry-After": str(self.window_seconds)},
            )

    def add_failure(self, key: str) -> None:

        self.failures.setdefault(key, []).append(time.monotonic())

    def reset(self, key: str) -> None:
        self.failures.pop(key, None)


login_limiter = FailedLoginLimiter(max_failures=5, window_seconds=300)