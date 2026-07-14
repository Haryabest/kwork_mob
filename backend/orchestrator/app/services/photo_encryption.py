"""E2E шифрование фото §10.6.2: ключ task→Redis, AES-256-GCM at rest в MinIO."""

from __future__ import annotations

import base64
import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import ENC_PREFIX
from app.models import Company
from app.services.company_policies import extract_policies

logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "photo_enc_key:"
KEY_TTL_SEC = 48 * 3600
ALGORITHM = "aes-256-gcm"


def is_encrypted_blob(data: bytes) -> bool:
    return data.startswith(ENC_PREFIX.encode("ascii"))


def _decode_task_key(key_b64: str) -> bytes:
    raw = base64.urlsafe_b64decode(key_b64.strip())
    if len(raw) != 32:
        raise ValueError("photo encryption key must be 32 bytes")
    return raw


def encrypt_photo_bytes(plaintext: bytes, key_b64: str) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = _decode_task_key(key_b64)
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    blob = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
    return f"{ENC_PREFIX}{blob}".encode("ascii")


def decrypt_photo_bytes(data: bytes, key_b64: str) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not is_encrypted_blob(data):
        return data
    text = data.decode("utf-8")
    raw = text[len(ENC_PREFIX) :]
    packed = base64.urlsafe_b64decode(raw.encode("ascii"))
    nonce, ciphertext = packed[:12], packed[12:]
    key = _decode_task_key(key_b64)
    return AESGCM(key).decrypt(nonce, ciphertext, None)


async def encryption_enabled_for_company(db: AsyncSession, company_id: int | None) -> bool:
    if not settings.PHOTO_E2E_ENCRYPTION_MASTER or not company_id:
        return False
    company = await db.get(Company, company_id)
    if not company:
        return False
    policies = extract_policies(company.settings)
    return bool(policies.get("e2e_photo_encryption"))


async def store_key(task_uuid: str, key_b64: str) -> None:
    from app.core.redis import get_redis

    _decode_task_key(key_b64)
    redis = await get_redis()
    await redis.set(f"{REDIS_KEY_PREFIX}{task_uuid}", key_b64.strip(), ex=KEY_TTL_SEC)
    logger.info("photo encryption key stored task=%s", task_uuid)


async def get_key(task_uuid: str) -> str | None:
    from app.core.redis import get_redis

    redis = await get_redis()
    val = await redis.get(f"{REDIS_KEY_PREFIX}{task_uuid}")
    if val is None:
        return None
    return val.decode() if isinstance(val, bytes) else val


async def delete_key(task_uuid: str) -> None:
    from app.core.redis import get_redis

    redis = await get_redis()
    await redis.delete(f"{REDIS_KEY_PREFIX}{task_uuid}")


def maybe_decrypt(data: bytes, key_b64: str | None) -> bytes:
    if not key_b64 or not is_encrypted_blob(data):
        return data
    return decrypt_photo_bytes(data, key_b64)
