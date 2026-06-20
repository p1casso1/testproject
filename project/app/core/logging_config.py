"""
Настройка логирования.

Используются два логгера:
  - "app"      — общий лог приложения (ошибки, AI, email, бизнес-логика)
  - "requests" — отдельный лог всех HTTP-запросов (для аудита/метрик)

Оба пишут в ротируемые файлы, чтобы логи не росли бесконечно.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

from app.config import get_settings


def _ensure_dir(path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def setup_logging() -> None:
    settings = get_settings()
    _ensure_dir(settings.log_file_path)
    _ensure_dir(settings.request_log_file_path)

    log_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --- Общий лог приложения ---
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.DEBUG if settings.app_debug else logging.INFO)
    app_logger.propagate = False
    if not app_logger.handlers:
        file_handler = RotatingFileHandler(
            settings.log_file_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(log_format)
        app_logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_format)
        app_logger.addHandler(console_handler)

    # --- Лог запросов ---
    request_logger = logging.getLogger("requests")
    request_logger.setLevel(logging.INFO)
    request_logger.propagate = False
    if not request_logger.handlers:
        req_handler = RotatingFileHandler(
            settings.request_log_file_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        req_handler.setFormatter(log_format)
        request_logger.addHandler(req_handler)


def get_app_logger() -> logging.Logger:
    return logging.getLogger("app")


def get_request_logger() -> logging.Logger:
    return logging.getLogger("requests")
