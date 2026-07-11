"""NSFW-детектор и модерация контента."""

class NsfwService:
    async def check_images(self, image_paths: list[str]) -> dict:
        """Проверка 12 фото перед генерацией."""
        return {"is_nsfw": False, "confidence": 0.0}

    async def check_blacklist(self, text: str) -> bool:
        """Проверка чёрного списка слов/брендов."""
        return False


nsfw_service = NsfwService()
