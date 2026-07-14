#!/usr/bin/env python3
"""Unit-тесты E2E шифрования фото §10.6.2."""

import base64
import os

import pytest

from app.services import photo_encryption as pe


@pytest.fixture
def task_key() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


def test_encrypt_decrypt_jpeg(task_key: str):
    plain = b"\xff\xd8\xff fake-jpeg-bytes"
    enc = pe.encrypt_photo_bytes(plain, task_key)
    assert pe.is_encrypted_blob(enc)
    out = pe.decrypt_photo_bytes(enc, task_key)
    assert out == plain


def test_plain_passthrough(task_key: str):
    plain = b"not-encrypted"
    assert pe.maybe_decrypt(plain, task_key) == plain
