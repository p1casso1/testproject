"""
Middleware:
  - присваивает каждому запросу уникальный request_id (для трассировки
    в логах и в ответах об ошибках)
  - логирует каждый входящий HTTP-запрос и время его обработки
"""
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging_config import get_request_logger

request_logger = get_request_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.perf_counter()

        client_ip = request.client.host if request.client else "unknown"

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            request_logger.error(
                "id=%s ip=%s method=%s path=%s status=500 duration_ms=%.2f (unhandled exception)",
                request_id,
                client_ip,
                request.method,
                request.url.path,
                duration_ms,
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        request_logger.info(
            "id=%s ip=%s method=%s path=%s status=%s duration_ms=%.2f",
            request_id,
            client_ip,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
