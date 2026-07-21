"""AES-256-GCM для ПД at rest (§2.7). Ключ — Vault или PD_ENCRYPTION_KEY."""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from functools import lru_cache

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

logger = logging.getLogger(__name__)

ENC_PREFIX = "enc:v1:"
_NONCE_LEN = 12
_KEY_LEN = 32


class CryptoConfigError(RuntimeError):
    """Ключ шифрования ПД не настроен."""


def _decode_key(raw: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(raw.strip())
    except Exception as exc:  # noqa: BLE001
        raise CryptoConfigError("PD_ENCRYPTION_KEY: неверный base64") from exc
    if len(key) != _KEY_LEN:
        raise CryptoConfigError(f"PD_ENCRYPTION_KEY: нужно {_KEY_LEN} байт после декодирования")
    return key


def _load_key_from_vault() -> bytes:
    if not settings.VAULT_ADDR or not settings.VAULT_TOKEN:
        raise CryptoConfigError("VAULT_ADDR и VAULT_TOKEN обязательны для загрузки ключа")
    path = settings.VAULT_PD_KEY_PATH.strip().lstrip("/")
    url = f"{settings.VAULT_ADDR.rstrip('/')}/v1/{path}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers={"X-Vault-Token": settings.VAULT_TOKEN})
        resp.raise_for_status()
        payload = resp.json()
    data = payload.get("data") or {}
    # KV v2: data.data.key; KV v1: data.key
    inner = data.get("data") if isinstance(data.get("data"), dict) else data
    key_b64 = inner.get("key") or inner.get("value") or inner.get("pd_encryption_key")
    if not key_b64:
        raise CryptoConfigError("Vault: ключ не найден в data.key / data.value")
    return _decode_key(str(key_b64))


def invalidate_pd_key_cache() -> None:
    """Сброс кэша ключа после ротации в Vault (§2.7)."""
    get_pd_encryption_key.cache_clear()


def pii_encryption_status() -> dict[str, object]:
    uses_vault = bool(settings.VAULT_ADDR and settings.VAULT_TOKEN and not settings.PD_ENCRYPTION_KEY)
    uses_env = bool(settings.PD_ENCRYPTION_KEY)
    source = "missing"
    if uses_vault:
        source = "vault"
    elif uses_env:
        source = "env"
    elif settings.is_development:
        source = "dev_fallback"
    ok = False
    error: str | None = None
    try:
        get_pd_encryption_key()
        ok = True
    except CryptoConfigError as exc:
        error = str(exc)
    return {
        "ok": ok,
        "source": source,
        "vault_path": settings.VAULT_PD_KEY_PATH if uses_vault else None,
        "error": error,
    }


def ensure_pii_encryption_ready() -> None:
    """Prod: ключ ПД обязателен (Vault или PD_ENCRYPTION_KEY)."""
    if settings.is_development:
        get_pd_encryption_key()
        return
    if not settings.PD_ENCRYPTION_KEY and not (settings.VAULT_ADDR and settings.VAULT_TOKEN):
        raise CryptoConfigError("Production: задайте PD_ENCRYPTION_KEY или VAULT_ADDR+VAULT_TOKEN")
    get_pd_encryption_key()


@lru_cache(maxsize=1)
def get_pd_encryption_key() -> bytes:
    if settings.PD_ENCRYPTION_KEY:
        return _decode_key(settings.PD_ENCRYPTION_KEY)
    if settings.VAULT_ADDR and settings.VAULT_TOKEN:
        key = _load_key_from_vault()
        logger.info("PD encryption key loaded from Vault (%s)", settings.VAULT_PD_KEY_PATH)
        return key
    if settings.is_development:
        derived = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        logger.warning("PD encryption: dev fallback from SECRET_KEY (не для prod)")
        return derived
    raise CryptoConfigError(
        "Задайте PD_ENCRYPTION_KEY или VAULT_ADDR+VAULT_TOKEN для шифрования ПД"
    )


def encrypt_field(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    text = str(plaintext)
    if not text:
        return None
    if text.startswith(ENC_PREFIX):
        return text
    key = get_pd_encryption_key()
    nonce = os.urandom(_NONCE_LEN)
    ciphertext = AESGCM(key).encrypt(nonce, text.encode("utf-8"), None)
    blob = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
    return f"{ENC_PREFIX}{blob}"


def decrypt_field(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value)
    if not text:
        return None
    if not text.startswith(ENC_PREFIX):
        return text
    raw = text[len(ENC_PREFIX) :]
    try:
        packed = base64.urlsafe_b64decode(raw.encode("ascii"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError("invalid encrypted payload") from exc
    if len(packed) <= _NONCE_LEN:
        raise ValueError("encrypted payload too short")
    nonce, ciphertext = packed[:_NONCE_LEN], packed[_NONCE_LEN:]
    key = get_pd_encryption_key()
    return AESGCM(key).decrypt(nonce, ciphertext, None).decode("utf-8")


def is_encrypted(value: str | None) -> bool:
    return bool(value and str(value).startswith(ENC_PREFIX))
