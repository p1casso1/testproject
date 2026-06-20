"""GET /api/metrics — агрегированная статистика обращений (хранится в файле)."""
from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import MetricsResponse
from app.repositories.metrics_repository import MetricsRepository

router = APIRouter(prefix="/api", tags=["metrics"])

_settings = get_settings()
_metrics_repository = MetricsRepository(_settings.metrics_storage_path)


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Статистика обращений",
    description="Возвращает количество запросов, разбивку по тональности/категориям и т.д.",
)
async def get_metrics() -> MetricsResponse:
    data = _metrics_repository.get()
    return MetricsResponse(**data)
