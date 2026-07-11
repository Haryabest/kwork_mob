"""Интеграция с Ollama для поддержки."""

import httpx

from app.core.config import settings


class OllamaService:
    async def suggest_reply(self, question: str, context: str = "") -> str:
        """Предложить ответ ИИ для сотрудника поддержки."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.OLLAMA_URL}/api/generate",
                json={"model": settings.OLLAMA_MODEL, "prompt": f"{context}\n\nВопрос: {question}"},
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json().get("response", "")


ollama_service = OllamaService()
