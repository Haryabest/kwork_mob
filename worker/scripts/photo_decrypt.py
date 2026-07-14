"""Расшифровка фото в RAM на воркере (§10.6.2)."""

from __future__ import annotations

import base64
import os
from pathlib import Path

ENC_PREFIX = b"enc:v1:"


def is_encrypted_blob(data: bytes) -> bool:
    return data.startswith(ENC_PREFIX)


def _decode_task_key(key_b64: str) -> bytes:
    raw = base64.urlsafe_b64decode(key_b64.strip())
    if len(raw) != 32:
        raise ValueError("photo encryption key must be 32 bytes")
    return raw


def decrypt_photo_bytes(data: bytes, key_b64: str) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not is_encrypted_blob(data):
        return data
    text = data.decode("utf-8")
    raw = text[len("enc:v1:") :]
    packed = base64.urlsafe_b64decode(raw.encode("ascii"))
    nonce, ciphertext = packed[:12], packed[12:]
    key = _decode_task_key(key_b64)
    return AESGCM(key).decrypt(nonce, ciphertext, None)


def decrypt_photos_dir(photos_dir: Path, key_b64: str) -> int:
    """Расшифровать view_* in-place (temp task dir). Возвращает число файлов."""
    count = 0
    for path in sorted(photos_dir.glob("view_*")):
        if not path.is_file():
            continue
        raw = path.read_bytes()
        if not is_encrypted_blob(raw):
            continue
        plain = decrypt_photo_bytes(raw, key_b64)
        path.write_bytes(plain)
        count += 1
    return count
