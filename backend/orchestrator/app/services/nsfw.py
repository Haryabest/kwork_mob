"""NSFW-детектор (§10.8): проверка 12 фото до постановки в очередь."""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
from typing import Any

from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AuditLog, NsfwBlock, Order, User
from app.services import photos as photos_service
from app.services.minio import minio_service

logger = logging.getLogger(__name__)

# Чёрный список слов/брендов (расширяется в админке позже)
DEFAULT_BLACKLIST = {
    "оружие",
    "наркотик",
    "кокаин",
    "героин",
    "порно",
    "xxx",
    "weapon",
    "drugs",
}


class NsfwService:
    def check_blacklist(self, text: str, extra_words: set[str] | None = None) -> bool:
        lowered = (text or "").lower()
        words = set(DEFAULT_BLACKLIST)
        if extra_words:
            words |= {w.lower() for w in extra_words}
        return any(w in lowered for w in words)

    async def check_blacklist_db(self, db: AsyncSession, text: str) -> bool:
        """Чёрный список из БД + defaults (§10.8)."""
        from app.services import blacklist as bl

        words = await bl.active_word_set(db)
        return self.check_blacklist(text, extra_words=words)

    def _download_photo_bytes(
        self, task_uuid: str, *, decryption_key: str | None = None
    ) -> list[tuple[str, bytes]]:
        from app.services import photo_encryption as photo_enc

        bucket = settings.MINIO_BUCKET_PHOTOS
        prefix = photos_service.photos_prefix(task_uuid)
        out: list[tuple[str, bytes]] = []
        for name in photos_service.VIEW_NAMES:
            key = f"{prefix}{name}"
            data = minio_service.download_bytes(bucket, key)
            data = photo_enc.maybe_decrypt(data, decryption_key)
            out.append((name, data))
        return out

    def _skin_ratio(self, data: bytes) -> float:
        """Эвристика: доля «телесных» пикселей в центральной области."""
        img = Image.open(io.BytesIO(data)).convert("RGB")
        w, h = img.size
        cx0, cy0 = int(w * 0.2), int(h * 0.15)
        cx1, cy1 = int(w * 0.8), int(h * 0.85)
        crop = img.crop((cx0, cy0, cx1, cy1))
        pixels = list(crop.getdata())
        if not pixels:
            return 0.0
        skin = 0
        for r, g, b in pixels:
            # классические YCbCr / RGB skin ranges
            if (
                r > 95
                and g > 40
                and b > 20
                and max(r, g, b) - min(r, g, b) > 15
                and abs(r - g) > 15
                and r > g
                and r > b
            ):
                skin += 1
        return skin / len(pixels)

    def _score_nudenet(self, data: bytes) -> float | None:
        try:
            from nudenet import NudeDetector  # type: ignore
        except Exception:  # noqa: BLE001
            return None
        try:
            detector = getattr(self, "_nudenet", None)
            if detector is None:
                detector = NudeDetector()
                self._nudenet = detector
            tmp = io.BytesIO(data)
            # NudeNet ожидает путь или ndarray — пишем во временный буфер через PIL
            import tempfile
            from pathlib import Path

            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / "frame.jpg"
                Image.open(tmp).convert("RGB").save(p, format="JPEG", quality=90)
                dets = detector.detect(str(p))
            bad_labels = {
                "FEMALE_GENITALIA_EXPOSED",
                "MALE_GENITALIA_EXPOSED",
                "BUTTOCKS_EXPOSED",
                "FEMALE_BREAST_EXPOSED",
                "ANUS_EXPOSED",
                "BELLY_EXPOSED",
            }
            scores = [float(d.get("score") or 0) for d in (dets or []) if d.get("class") in bad_labels]
            return max(scores) if scores else 0.0
        except Exception as exc:  # noqa: BLE001
            logger.warning("NudeNet failed: %s", exc)
            return None

    def _analyze_image(self, name: str, data: bytes) -> dict[str, Any]:
        mode = settings.NSFW_MODE.lower()
        threshold = settings.NSFW_THRESHOLD

        if settings.NSFW_FORCE_BLOCK:
            return {
                "name": name,
                "is_nsfw": True,
                "confidence": 1.0,
                "method": "force",
            }

        # Маркер для E2E без реального NSFW-контента: файл начинается с magic JPEG + EXIF comment
        if b"NSFW_TEST_BLOCK" in data[:4096]:
            return {"name": name, "is_nsfw": True, "confidence": 1.0, "method": "marker"}

        confidence = 0.0
        method = "none"

        if mode in ("nudenet", "auto"):
            nn = self._score_nudenet(data)
            if nn is not None:
                confidence = nn
                method = "nudenet"

        if method == "none" or (mode in ("heuristic", "auto") and confidence < threshold):
            skin = self._skin_ratio(data)
            # высокая доля кожи → подозрительно для товарных фото
            if skin > confidence:
                confidence = skin
                method = "skin_heuristic"

        return {
            "name": name,
            "is_nsfw": confidence >= threshold,
            "confidence": round(confidence, 4),
            "method": method,
        }

    async def check_images(self, image_paths: list[str]) -> dict:
        """Совместимость: пути на диске."""
        frames = []
        for p in image_paths:
            with open(p, "rb") as f:
                frames.append((p, f.read()))
        return self._aggregate([self._analyze_image(n, d) for n, d in frames])

    async def check_task_photos(
        self, task_uuid: str, *, decryption_key: str | None = None
    ) -> dict[str, Any]:
        """Проверка 12 ракурсов из MinIO перед очередью."""
        if settings.NSFW_MODE.lower() == "off":
            return {"is_nsfw": False, "confidence": 0.0, "method": "off", "frames": []}

        photos = await asyncio.to_thread(
            self._download_photo_bytes, task_uuid, decryption_key=decryption_key
        )
        frames = await asyncio.to_thread(
            lambda: [self._analyze_image(n, d) for n, d in photos]
        )
        result = self._aggregate(frames)
        # хэш для аудита
        h = hashlib.sha256()
        for _, data in photos:
            h.update(data[:8192])
        result["photo_hash"] = h.hexdigest()
        return result

    def _aggregate(self, frames: list[dict]) -> dict[str, Any]:
        if not frames:
            return {"is_nsfw": False, "confidence": 0.0, "frames": []}
        worst = max(frames, key=lambda f: f.get("confidence") or 0)
        is_nsfw = any(f.get("is_nsfw") for f in frames)
        return {
            "is_nsfw": is_nsfw,
            "confidence": worst.get("confidence") or 0.0,
            "method": worst.get("method"),
            "trigger": worst.get("name"),
            "frames": frames,
        }

    async def block_order(
        self,
        db: AsyncSession,
        *,
        order: Order,
        user: User,
        result: dict[str, Any],
        refund: bool = True,
        charged: bool = False,
    ) -> NsfwBlock:
        """Блок заказа + refund (если уже списали) + временная блокировка аккаунта."""
        order.status = "blocked_nsfw"
        reason = f"nsfw:{result.get('method') or 'auto'}"
        if len(reason) > 50:
            reason = reason[:50]

        refunded = False
        refund_meta: dict = {}
        if refund and charged and order.amount > 0:
            from app.services.refunds import refund_order

            refund_meta = await refund_order(
                db, order, reason=f"NSFW auto block", user=user, prefer_card=True
            )
            refunded = bool(refund_meta.get("refunded"))
        elif refund and not charged:
            refunded = True

        if user.status not in ("blocked_permanent",):
            user.status = "blocked_pending_review"

        block = NsfwBlock(
            order_id=order.id,
            user_id=user.id,
            reason=reason,
            refunded=refunded,
            verified=False,
        )
        db.add(block)
        db.add(
            AuditLog(
                company_id=order.company_id,
                user_id=user.id,
                action="nsfw_auto_block",
                details={
                    "order_id": order.id,
                    "task_uuid": order.task_uuid,
                    "confidence": result.get("confidence"),
                    "method": result.get("method"),
                    "trigger": result.get("trigger"),
                    "photo_hash": result.get("photo_hash"),
                    "refunded": refunded,
                    "refund": refund_meta,
                },
            )
        )
        await db.flush()
        logger.warning(
            "NSFW block order=%s user=%s conf=%.3f method=%s",
            order.id,
            user.id,
            float(result.get("confidence") or 0),
            result.get("method"),
        )
        try:
            from app.services.task_lifecycle import _notify_order_user_push

            refund_note = " Средства возвращены." if refunded else ""
            await _notify_order_user_push(
                db,
                order,
                pref_key="nsfw_blocked",
                event_type="nsfw_blocked",
                title="NSFW-блокировка",
                body=(
                    f"Заказ #{order.id} отклонён.{refund_note} "
                    "Аккаунт на проверке до 24 ч."
                ),
            )
            if refunded and order.amount > 0:
                await _notify_order_user_push(
                    db,
                    order,
                    pref_key="refund",
                    event_type="refund",
                    title="Возврат средств",
                    body=f"По заказу #{order.id} средства возвращены.",
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("NSFW user push failed: %s", exc)
        try:
            from app.services.alerts import notify_nsfw_block

            await notify_nsfw_block(
                order_id=order.id,
                user_id=user.id,
                confidence=float(result.get("confidence") or 0),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("NSFW alert failed: %s", exc)
        return block


nsfw_service = NsfwService()
