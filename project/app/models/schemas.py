"""
Pydantic-схемы: валидация входящих запросов и формат ответов API.
"""
import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class ContactRequest(BaseModel):
    """Тело запроса для POST /api/contact"""

    name: str = Field(..., min_length=2, max_length=100, description="Имя отправителя")
    phone: str = Field(..., min_length=5, max_length=20, description="Телефон в любом формате")
    email: EmailStr = Field(..., description="Email отправителя")
    comment: str = Field(..., min_length=5, max_length=2000, description="Текст обращения")

    @field_validator("name")
    @classmethod
    def name_must_be_meaningful(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Имя не может быть пустым")
        if not re.search(r"[A-Za-zА-Яа-яЁё]", v):
            raise ValueError("Имя должно содержать буквы")
        return v

    @field_validator("phone")
    @classmethod
    def phone_must_be_valid(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.fullmatch(r"\+?\d{5,15}", cleaned):
            raise ValueError(
                "Телефон должен содержать только цифры, пробелы, скобки, дефисы и опциональный +"
            )
        return v.strip()

    @field_validator("comment")
    @classmethod
    def comment_must_not_be_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Комментарий не может быть пустым")
        return v


class AIAnalysis(BaseModel):
    """Результат AI-обработки обращения."""

    sentiment: str = Field(..., description="positive | neutral | negative")
    category: str = Field(..., description="Тип обращения, определённый AI")
    auto_reply: str = Field(..., description="Автоматически сгенерированный черновик ответа")
    provider: str = Field(..., description="anthropic | fallback")
    confidence: Optional[float] = None


class ContactResponse(BaseModel):
    """Ответ API на успешную обработку обращения."""

    success: bool = True
    message: str
    request_id: str
    ai_analysis: AIAnalysis
    owner_email_sent: bool
    user_email_sent: bool
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Единый формат ошибки для всего API."""

    success: bool = False
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    ai_provider_configured: bool
    smtp_configured: bool


class MetricsResponse(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    sentiment_breakdown: dict
    category_breakdown: dict
    last_request_at: Optional[datetime] = None
    rate_limited_requests: int
