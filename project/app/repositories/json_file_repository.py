"""
Базовый репозиторий для хранения данных в JSON-файлах на диске.

Это сознательное решение по заданию: БД не обязательна, файловая
система используется для логов, метрик, rate limiting и заявок.
Доступ к файлу защищён потоковой блокировкой (threading.Lock),
чтобы избежать гонок при параллельных запросах внутри одного процесса.
"""
import json
import os
import threading
from typing import Any

from app.core.exceptions import StorageException


class JSONFileRepository:
    """Простой потокобезопасный key-value/JSON репозиторий поверх файла."""

    _locks: dict[str, threading.Lock] = {}
    _locks_guard = threading.Lock()

    def __init__(self, file_path: str, default: Any):
        self.file_path = file_path
        self.default = default
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        self._lock = self._get_lock(file_path)
        if not os.path.exists(file_path):
            self._write_unlocked(default)

    @classmethod
    def _get_lock(cls, path: str) -> threading.Lock:
        with cls._locks_guard:
            if path not in cls._locks:
                cls._locks[path] = threading.Lock()
            return cls._locks[path]

    def _write_unlocked(self, data: Any) -> None:
        tmp_path = f"{self.file_path}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            os.replace(tmp_path, self.file_path)
        except OSError as exc:
            raise StorageException(
                f"Не удалось записать в {self.file_path}", detail=str(exc)
            ) from exc

    def read(self) -> Any:
        with self._lock:
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        return self.default
                    return json.loads(content)
            except FileNotFoundError:
                return self.default
            except json.JSONDecodeError:
                # Файл повреждён (например, обрыв записи) — не валим сервис,
                # просто откатываемся на дефолтное значение.
                return self.default

    def write(self, data: Any) -> None:
        with self._lock:
            self._write_unlocked(data)

    def update(self, mutate_fn) -> Any:
        """Атомарно читает, применяет функцию-мутатор и сохраняет результат."""
        with self._lock:
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    current = json.loads(content) if content else self.default
            except (FileNotFoundError, json.JSONDecodeError):
                current = self.default

            new_data = mutate_fn(current)
            self._write_unlocked(new_data)
            return new_data
