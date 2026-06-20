"""
Сервис rate limiting на основе файлового хранилища (sliding window).

Защищает POST /api/contact от спама: не более N запросов с одного
IP в течение заданного окна времени (по умолчанию 5 запросов/час).
"""
from app.config import get_settings
from app.core.exceptions import RateLimitExceededException
from app.core.logging_config import get_app_logger
from app.repositories.rate_limit_repository import RateLimitRepository

logger = get_app_logger()


class RateLimiterService:
    def __init__(self):
        settings = get_settings()
        self.max_requests = settings.rate_limit_max_requests
        self.window_seconds = settings.rate_limit_window_seconds
        self._repo = RateLimitRepository(settings.rate_limit_storage_path)

    def check_and_register(self, client_ip: str) -> None:
        """Поднимает RateLimitExceededException, если лимит превышен.
        Иначе — регистрирует текущий запрос."""
        existing = self._repo.get_recent_requests(client_ip, self.window_seconds)

        if len(existing) >= self.max_requests:
            logger.warning(
                "Rate limit exceeded for ip=%s (%d requests in last %ds)",
                client_ip,
                len(existing),
                self.window_seconds,
            )
            raise RateLimitExceededException(
                "Превышен лимит запросов. Попробуйте позже.",
                detail=(
                    f"Максимум {self.max_requests} запросов за "
                    f"{self.window_seconds // 60} минут"
                ),
            )

        self._repo.register_request(client_ip, self.window_seconds)
