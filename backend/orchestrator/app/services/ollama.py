"""Интеграция с Ollama для поддержки (§4.8.11 / §14.4)."""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaService:
    @property
    def available(self) -> bool:
        return bool(settings.OLLAMA_URL)

    async def health(self) -> dict:
        if not settings.OLLAMA_URL:
            return {"ok": False, "reason": "OLLAMA_URL empty"}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.OLLAMA_URL.rstrip('/')}/api/tags")
                return {"ok": resp.status_code < 400, "status_code": resp.status_code}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "reason": str(exc)[:200]}

    async def suggest_reply(self, question: str, context: str = "") -> str:
        """Предложить ответ ИИ для сотрудника поддержки."""
        prompt = (
            "Ты сотрудник поддержки сервиса 3D-моделей для маркетплейсов. "
            "Ответь кратко и по делу на русском.\n\n"
            f"{context}\n\nВопрос пользователя: {question}\n\nОтвет:"
        )
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{settings.OLLAMA_URL.rstrip('/')}/api/generate",
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                return (response.json().get("response") or "").strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning("ollama suggest_reply failed: %s", exc)
            raise


ollama_service = OllamaService()
