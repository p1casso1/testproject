"""
Глобальная обработка ошибок.

Все исключения — как ожидаемые (AppException и потомки), так и
непредвиденные — приводятся к единому JSON-формату ErrorResponse,
со cоответствующим HTTP-статусом, и обязательно логируются.
"""
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException
from app.core.logging_config import get_app_logger

logger = get_app_logger()


def _error_payload(error: str, detail: str | None, request_id: str) -> dict:
    return {
        "success": False,
        "error": error,
        "detail": detail,
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.warning(
            "AppException [%s] on %s %s -> %s",
            exc.error_code,
            request.method,
            request.url.path,
            exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(exc.error_code, exc.detail or exc.message, request_id),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        errors = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        logger.info("Validation error on %s %s -> %s", request.method, request.url.path, errors)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_payload("validation_error", errors, request_id),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.error(
            "Unhandled exception on %s %s: %s",
            request.method,
            request.url.path,
            repr(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload(
                "internal_error", "Внутренняя ошибка сервера. Уже залогировано.", request_id
            ),
        )
