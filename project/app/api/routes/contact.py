"""
Controller-слой для обращений с формы обратной связи.

Тонкий слой: только разбор HTTP-запроса, rate limiting и делегирование
бизнес-логики в ContactService. Никакой бизнес-логики тут быть не должно.
"""
from fastapi import APIRouter, Request, status

from app.config import get_settings
from app.models.schemas import ContactRequest, ContactResponse, ErrorResponse
from app.repositories.metrics_repository import MetricsRepository
from app.services.contact_service import ContactService
from app.services.rate_limiter import RateLimiterService

router = APIRouter(prefix="/api", tags=["contact"])

_settings = get_settings()
_contact_service = ContactService()
_rate_limiter = RateLimiterService()
_metrics_repository = MetricsRepository(_settings.metrics_storage_path)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post(
    "/contact",
    response_model=ContactResponse,
    status_code=status.HTTP_200_OK,
    responses={
        422: {"model": ErrorResponse, "description": "Ошибка валидации входных данных"},
        429: {"model": ErrorResponse, "description": "Превышен лимит запросов"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
    summary="Отправить обращение через форму обратной связи",
    description=(
        "Принимает имя, телефон, email и комментарий. Валидирует данные, "
        "анализирует комментарий через AI (тональность, категория, черновик ответа), "
        "отправляет email-уведомления владельцу сайта и копию пользователю, "
        "и сохраняет обращение/метрики в файловое хранилище. "
        "Защищено rate limiting'ом по IP."
    ),
)
async def submit_contact_form(payload: ContactRequest, request: Request) -> ContactResponse:
    client_ip = _get_client_ip(request)

    try:
        _rate_limiter.check_and_register(client_ip)
    except Exception:
        _metrics_repository.record_rate_limited()
        raise

    try:
        return await _contact_service.handle_contact_request(payload)
    except Exception:
        _metrics_repository.record_failure()
        raise
