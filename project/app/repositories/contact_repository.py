"""
Хранилище самих обращений (для истории / отладки / возможного
повторного использования AI-анализа). Хранится последние N записей.
"""
from datetime import datetime, timezone

from app.repositories.json_file_repository import JSONFileRepository

_MAX_STORED_CONTACTS = 500


class ContactRepository:
    def __init__(self, file_path: str):
        self._repo = JSONFileRepository(file_path, default=[])

    def save(self, request_id: str, name: str, phone: str, email: str, comment: str, ai_result: dict) -> None:
        def mutate(data: list) -> list:
            data.append(
                {
                    "request_id": request_id,
                    "name": name,
                    "phone": phone,
                    "email": email,
                    "comment": comment,
                    "ai_analysis": ai_result,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            # ограничиваем размер файла, чтобы он не рос бесконечно
            return data[-_MAX_STORED_CONTACTS:]

        self._repo.update(mutate)

    def list_recent(self, limit: int = 50) -> list:
        data = self._repo.read()
        return data[-limit:][::-1]
