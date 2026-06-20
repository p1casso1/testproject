"""
Кастомные исключения приложения.

Каждое исключение знает свой HTTP-статус — это позволяет глобальному
error handler'у (app/core/error_handlers.py) формировать единый
формат ответа для любой ошибки в системе.
"""


class AppException(Exception):
    """Базовое исключение приложения."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, detail: str | None = None):
        self.message = message
        self.detail = detail
        super().__init__(message)


class ValidationException(AppException):
    status_code = 422
    error_code = "validation_error"


class RateLimitExceededException(AppException):
    status_code = 429
    error_code = "rate_limit_exceeded"


class EmailDeliveryException(AppException):
    """Не используется для прерывания запроса — только для логирования,
    т.к. сбой почты не должен валить весь запрос (graceful degradation)."""

    status_code = 502
    error_code = "email_delivery_failed"


class StorageException(AppException):
    status_code = 500
    error_code = "storage_error"
