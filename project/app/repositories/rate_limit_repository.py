"""
Хранилище данных rate limiting в JSON-файле.

Структура файла:
{
  "<ip_address>": [<unix_timestamp>, <unix_timestamp>, ...],
  ...
}
Для каждого IP хранится список временных меток запросов,
попадающих в текущее скользящее окно.
"""
import time

from app.repositories.json_file_repository import JSONFileRepository


class RateLimitRepository:
    def __init__(self, file_path: str):
        self._repo = JSONFileRepository(file_path, default={})

    def register_request(self, ip: str, window_seconds: int) -> list[float]:
        """Регистрирует новый запрос и возвращает актуальный список timestamp'ов
        внутри окна (уже без устаревших записей)."""
        now = time.time()

        def mutate(data: dict) -> dict:
            timestamps = data.get(ip, [])
            timestamps = [t for t in timestamps if now - t < window_seconds]
            timestamps.append(now)
            data[ip] = timestamps
            return data

        new_data = self._repo.update(mutate)
        return new_data.get(ip, [])

    def get_recent_requests(self, ip: str, window_seconds: int) -> list[float]:
        now = time.time()
        data = self._repo.read()
        timestamps = data.get(ip, [])
        return [t for t in timestamps if now - t < window_seconds]
