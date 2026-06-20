"""GET /api/health — проверка статуса сервиса и его зависимостей."""
from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])

APP_VERSION = "1.0.0"


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Проверка статуса сервиса",
    description="Возвращает статус сервиса и информацию о том, настроены ли AI и SMTP интеграции.",
)
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc),
        version=APP_VERSION,
        ai_provider_configured=bool(settings.ai_enabled and settings.anthropic_api_key),
        smtp_configured=bool(
            settings.smtp_host and settings.smtp_user and settings.smtp_password and settings.owner_email
        ),
    )
