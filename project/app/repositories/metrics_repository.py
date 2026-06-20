"""
Хранилище агрегированной статистики обращений (для GET /api/metrics).
"""
from datetime import datetime, timezone

from app.repositories.json_file_repository import JSONFileRepository

_DEFAULT_METRICS = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "rate_limited_requests": 0,
    "sentiment_breakdown": {"positive": 0, "neutral": 0, "negative": 0},
    "category_breakdown": {},
    "last_request_at": None,
}


class MetricsRepository:
    def __init__(self, file_path: str):
        self._repo = JSONFileRepository(file_path, default=dict(_DEFAULT_METRICS))

    def record_success(self, sentiment: str, category: str) -> None:
        def mutate(data: dict) -> dict:
            data.setdefault("sentiment_breakdown", {"positive": 0, "neutral": 0, "negative": 0})
            data.setdefault("category_breakdown", {})
            data["total_requests"] = data.get("total_requests", 0) + 1
            data["successful_requests"] = data.get("successful_requests", 0) + 1
            data["sentiment_breakdown"][sentiment] = (
                data["sentiment_breakdown"].get(sentiment, 0) + 1
            )
            data["category_breakdown"][category] = (
                data["category_breakdown"].get(category, 0) + 1
            )
            data["last_request_at"] = datetime.now(timezone.utc).isoformat()
            return data

        self._repo.update(mutate)

    def record_failure(self) -> None:
        def mutate(data: dict) -> dict:
            data["total_requests"] = data.get("total_requests", 0) + 1
            data["failed_requests"] = data.get("failed_requests", 0) + 1
            data["last_request_at"] = datetime.now(timezone.utc).isoformat()
            return data

        self._repo.update(mutate)

    def record_rate_limited(self) -> None:
        def mutate(data: dict) -> dict:
            data["rate_limited_requests"] = data.get("rate_limited_requests", 0) + 1
            return data

        self._repo.update(mutate)

    def get(self) -> dict:
        data = self._repo.read()
        merged = dict(_DEFAULT_METRICS)
        merged.update(data)
        return merged
