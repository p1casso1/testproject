"""
Конфигурация приложения.

Все настройки читаются из переменных окружения (.env) с помощью
pydantic-settings. Это даёт валидацию типов "из коробки" и единое
место, откуда конфигурация раздаётся во все слои приложения.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Приложение ---
    app_name: str = "Developer Landing Backend"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # --- CORS ---
    cors_origins: str = "http://localhost:3000"

    # --- SMTP ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    mail_from: str = ""
    mail_from_name: str = "Developer Portfolio"
    owner_email: str = ""

    # --- AI ---
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-20241022"
    ai_timeout_seconds: int = 8
    ai_enabled: bool = True

    # --- Rate limiting ---
    rate_limit_max_requests: int = 5
    rate_limit_window_seconds: int = 3600
    rate_limit_storage_path: str = "data/rate_limit.json"

    # --- Хранилища ---
    log_file_path: str = "logs/app.log"
    request_log_file_path: str = "logs/requests.log"
    metrics_storage_path: str = "data/metrics.json"
    contacts_storage_path: str = "data/contacts.json"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Settings кэшируются — файл .env читается один раз за время жизни процесса."""
    return Settings()
