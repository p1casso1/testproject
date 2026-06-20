"""
Точка входа приложения.

Собирает воедино: конфигурацию, логирование, middleware, CORS,
обработчики ошибок и роутеры. Swagger/OpenAPI документация доступна
автоматически на /docs (Swagger UI) и /redoc (ReDoc).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import contact, health, metrics
from app.config import get_settings
from app.core.error_handlers import register_error_handlers
from app.core.logging_config import get_app_logger, setup_logging
from app.core.middleware import RequestLoggingMiddleware

settings = get_settings()
setup_logging()
logger = get_app_logger()

app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend API для лендинг-презентации разработчика: форма обратной связи "
        "с валидацией, email-уведомлениями, AI-анализом обращений (тональность, "
        "категория, авто-ответ), rate limiting'ом и файловым хранением логов/метрик."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# --- Request logging / request-id middleware ---
app.add_middleware(RequestLoggingMiddleware)

# --- Глобальные обработчики ошибок ---
register_error_handlers(app)

# --- Роутеры ---
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(contact.router)

# --- Статика фронтенда (бонусная часть задания) ---
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/", tags=["root"])
async def root():
    """Редирект-инфо на корне API. Сама лендинг-страница — на /static/index.html"""
    return {
        "service": settings.app_name,
        "status": "running",
        "docs": "/docs",
        "frontend": "/static/index.html",
        "health": "/api/health",
    }


@app.on_event("startup")
async def on_startup():
    logger.info("=" * 60)
    logger.info("%s starting up (env=%s)", settings.app_name, settings.app_env)
    logger.info("AI enabled: %s | SMTP configured: %s",
                bool(settings.ai_enabled and settings.anthropic_api_key),
                bool(settings.smtp_host and settings.smtp_user and settings.owner_email))
    logger.info("=" * 60)


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("%s shutting down", settings.app_name)
