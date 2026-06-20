"""
AI-сервис: анализ тональности, классификация и генерация черновика
ответа на обращение пользователя.

Основной провайдер — Anthropic Claude API.
Если AI отключён конфигурацией, ключ не задан, истёк таймаут или
провайдер вернул ошибку — сервис прозрачно переключается на простой
rule-based fallback (по ключевым словам), чтобы основной бизнес-процесс
(приём заявки и отправка писем) никогда не падал из-за AI.
"""
import asyncio
import json
import re

import anthropic

from app.config import get_settings
from app.core.logging_config import get_app_logger
from app.models.schemas import AIAnalysis

logger = get_app_logger()

_SYSTEM_PROMPT = """Ты — ассистент, который анализирует обращения с формы обратной связи
на сайте разработчика-фрилансера. Для каждого обращения верни ТОЛЬКО валидный JSON
(без markdown, без пояснений) со следующими полями:

{
  "sentiment": "positive" | "neutral" | "negative",
  "category": одна из ["project_inquiry", "job_offer", "collaboration", "complaint", "question", "spam", "other"],
  "auto_reply": "Короткий (2-4 предложения) дружелюбный черновик ответа на русском или языке обращения, который менеджер может отредактировать перед отправкой"
}

Не добавляй ничего, кроме JSON."""

_POSITIVE_WORDS = {
    "спасибо", "отлично", "круто", "супер", "понравилось", "благодарю",
    "great", "thanks", "thank you", "awesome", "love", "excellent",
}
_NEGATIVE_WORDS = {
    "плохо", "ужасно", "недоволен", "проблема", "не работает", "обман",
    "bad", "terrible", "awful", "scam", "broken", "angry", "disappointed",
}
_SPAM_PATTERNS = re.compile(
    r"(viagra|casino|crypto airdrop|click here|http[s]?://\S+\s+http[s]?://\S+)",
    re.IGNORECASE,
)


def _fallback_analysis(comment: str) -> AIAnalysis:
    """Простая rule-based эвристика — используется, когда AI недоступен."""
    lowered = comment.lower()

    if _SPAM_PATTERNS.search(lowered):
        category = "spam"
        sentiment = "neutral"
    else:
        category = "other"
        sentiment = "neutral"
        if any(word in lowered for word in _POSITIVE_WORDS):
            sentiment = "positive"
        elif any(word in lowered for word in _NEGATIVE_WORDS):
            sentiment = "negative"

        if any(w in lowered for w in ["не работает", "ошибка", "баг", "сломан", "не открывается"]):
            category = "complaint"
        elif any(w in lowered for w in ["вакансия", "нанять", "job offer", "hire you", "hire me"]):
            category = "job_offer"
        elif any(w in lowered for w in ["проект", "разработать", "сделать сайт", "project"]):
            category = "project_inquiry"
        elif any(w in lowered for w in ["сотрудничество", "партнёрство", "collaborate"]):
            category = "collaboration"
        elif "?" in comment:
            category = "question"
        elif sentiment == "negative":
            category = "complaint"

    auto_reply = (
        "Спасибо за обращение! Мы получили ваше сообщение и ответим "
        "в ближайшее время. Если вопрос срочный — укажите это, пожалуйста, "
        "в повторном письме."
    )

    return AIAnalysis(
        sentiment=sentiment,
        category=category,
        auto_reply=auto_reply,
        provider="fallback",
        confidence=None,
    )


class AIService:
    def __init__(self):
        settings = get_settings()
        self.enabled = settings.ai_enabled and bool(settings.anthropic_api_key)
        self.model = settings.anthropic_model
        self.timeout_seconds = settings.ai_timeout_seconds
        self._client = (
            anthropic.Anthropic(api_key=settings.anthropic_api_key) if self.enabled else None
        )

    def _call_anthropic_sync(self, comment: str) -> AIAnalysis:
        message = self._client.messages.create(
            model=self.model,
            max_tokens=400,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Обращение пользователя:\n\n{comment}"}],
        )
        raw_text = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        ).strip()

        # Модель иногда оборачивает JSON в ```json ... ``` несмотря на инструкцию — подчищаем.
        cleaned = re.sub(r"^```json|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(cleaned)

        return AIAnalysis(
            sentiment=parsed.get("sentiment", "neutral"),
            category=parsed.get("category", "other"),
            auto_reply=parsed.get("auto_reply", ""),
            provider="anthropic",
            confidence=None,
        )

    async def analyze_comment(self, comment: str) -> AIAnalysis:
        if not self.enabled:
            logger.info("AI disabled or no API key configured — using fallback analysis")
            return _fallback_analysis(comment)

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self._call_anthropic_sync, comment),
                timeout=self.timeout_seconds,
            )
            logger.info("AI analysis succeeded via Anthropic: sentiment=%s category=%s",
                        result.sentiment, result.category)
            return result
        except asyncio.TimeoutError:
            logger.warning("Anthropic API timed out after %ss — falling back", self.timeout_seconds)
            return _fallback_analysis(comment)
        except (anthropic.APIError, anthropic.APIConnectionError, anthropic.RateLimitError) as exc:
            logger.warning("Anthropic API error (%s) — falling back", repr(exc))
            return _fallback_analysis(comment)
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Failed to parse Anthropic response (%s) — falling back", repr(exc))
            return _fallback_analysis(comment)
        except Exception as exc:  # noqa: BLE001 — намеренно широкий перехват для graceful fallback
            logger.error("Unexpected AI error (%s) — falling back", repr(exc), exc_info=True)
            return _fallback_analysis(comment)
