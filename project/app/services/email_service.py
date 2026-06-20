"""
Email-сервис: отправка письма владельцу сайта и копии пользователю.

Если SMTP не настроен или произошла ошибка отправки — сервис НЕ
прерывает обработку запроса (графический fallback): ошибка логируется,
а API всё равно возвращает успешный ответ с пометкой, что письмо
не было отправлено.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings
from app.core.logging_config import get_app_logger
from app.models.schemas import AIAnalysis

logger = get_app_logger()


class EmailService:
    def __init__(self):
        settings = get_settings()
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.use_tls = settings.smtp_use_tls
        self.mail_from = settings.mail_from or settings.smtp_user
        self.mail_from_name = settings.mail_from_name
        self.owner_email = settings.owner_email
        self.configured = bool(self.host and self.user and self.password and self.owner_email)

    def _send_sync(self, to_email: str, subject: str, body: str) -> None:
        msg = MIMEMultipart()
        msg["From"] = f"{self.mail_from_name} <{self.mail_from}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(self.host, self.port, timeout=10) as server:
            if self.use_tls:
                server.starttls()
            server.login(self.user, self.password)
            server.sendmail(self.mail_from, [to_email], msg.as_string())

    def _owner_email_body(self, name: str, phone: str, email: str, comment: str, ai: AIAnalysis) -> str:
        return (
            f"Новое обращение через форму обратной связи на сайте.\n\n"
            f"Имя: {name}\n"
            f"Телефон: {phone}\n"
            f"Email: {email}\n\n"
            f"Комментарий:\n{comment}\n\n"
            f"--- AI-анализ ({ai.provider}) ---\n"
            f"Тональность: {ai.sentiment}\n"
            f"Категория: {ai.category}\n"
            f"Черновик ответа:\n{ai.auto_reply}\n"
        )

    def _user_email_body(self, name: str, comment: str, ai: AIAnalysis) -> str:
        return (
            f"Здравствуйте, {name}!\n\n"
            f"Спасибо за ваше обращение. Мы получили его и скоро свяжемся с вами.\n\n"
            f"Ваше сообщение:\n{comment}\n\n"
            f"{ai.auto_reply}\n\n"
            f"---\nЭто автоматическое уведомление, отвечать на него не нужно."
        )

    def send_contact_notifications(
        self, name: str, phone: str, email: str, comment: str, ai: AIAnalysis
    ) -> tuple[bool, bool]:
        """Возвращает (owner_email_sent, user_email_sent). Никогда не бросает исключение."""
        if not self.configured:
            logger.warning(
                "SMTP не настроен (host/user/password/owner_email) — письма не отправлены, "
                "но запрос продолжает обработку (graceful fallback)"
            )
            return False, False

        owner_sent = False
        user_sent = False

        try:
            self._send_sync(
                self.owner_email,
                f"Новое обращение от {name}",
                self._owner_email_body(name, phone, email, comment, ai),
            )
            owner_sent = True
        except Exception as exc:  # noqa: BLE001
            logger.error("Не удалось отправить письмо владельцу: %s", repr(exc))

        try:
            self._send_sync(
                email,
                "Мы получили ваше обращение",
                self._user_email_body(name, comment, ai),
            )
            user_sent = True
        except Exception as exc:  # noqa: BLE001
            logger.error("Не удалось отправить письмо-копию пользователю: %s", repr(exc))

        return owner_sent, user_sent
