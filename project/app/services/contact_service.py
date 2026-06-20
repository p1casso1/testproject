"""
Сервис обращений — оркестрирует полный бизнес-процесс:

  валидация (уже выполнена Pydantic на уровне роутера)
    -> AI-анализ комментария (с fallback)
    -> отправка email-уведомлений (owner + копия пользователю, с fallback)
    -> сохранение в файловое хранилище (история + метрики)
    -> формирование ответа
"""
import asyncio
import uuid
from datetime import datetime, timezone

from app.config import get_settings
from app.core.logging_config import get_app_logger
from app.models.schemas import ContactRequest, ContactResponse
from app.repositories.contact_repository import ContactRepository
from app.repositories.metrics_repository import MetricsRepository
from app.services.ai_service import AIService
from app.services.email_service import EmailService

logger = get_app_logger()


class ContactService:
    def __init__(self):
        settings = get_settings()
        self.ai_service = AIService()
        self.email_service = EmailService()
        self.contact_repository = ContactRepository(settings.contacts_storage_path)
        self.metrics_repository = MetricsRepository(settings.metrics_storage_path)

    async def handle_contact_request(self, payload: ContactRequest) -> ContactResponse:
        request_id = str(uuid.uuid4())
        logger.info(
            "Processing contact request id=%s from email=%s", request_id, payload.email
        )

        # 1. AI-анализ обращения (тональность, категория, черновик ответа)
        ai_analysis = await self.ai_service.analyze_comment(payload.comment)

        # 2. Отправка email-уведомлений (блокирующий smtplib — выносим в отдельный поток)
        owner_sent, user_sent = await asyncio.to_thread(
            self.email_service.send_contact_notifications,
            payload.name,
            payload.phone,
            payload.email,
            payload.comment,
            ai_analysis,
        )

        # 3. Сохраняем обращение и обновляем метрики
        try:
            self.contact_repository.save(
                request_id=request_id,
                name=payload.name,
                phone=payload.phone,
                email=payload.email,
                comment=payload.comment,
                ai_result=ai_analysis.model_dump(),
            )
            self.metrics_repository.record_success(ai_analysis.sentiment, ai_analysis.category)
        except Exception as exc:  # noqa: BLE001 — хранение не должно ронять успешный ответ
            logger.error("Не удалось сохранить обращение/метрики: %s", repr(exc), exc_info=True)

        logger.info("Contact request id=%s processed successfully", request_id)

        return ContactResponse(
            success=True,
            message="Спасибо! Ваше обращение получено и обрабатывается.",
            request_id=request_id,
            ai_analysis=ai_analysis,
            owner_email_sent=owner_sent,
            user_email_sent=user_sent,
            timestamp=datetime.now(timezone.utc),
        )
