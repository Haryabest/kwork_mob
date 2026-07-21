"""§5.1 polycount, §5.2 marketplace compression, §5.3 watermark admin, CI rate-limit skip."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from app.services import gateway_rate_limit as gw_rl

WORKER_SCRIPTS = Path(__file__).resolve().parents[3] / "worker" / "scripts"


def _load_worker_module(name: str):
    path = WORKER_SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


category_targets = _load_worker_module("category_targets")
marketplace_limits = _load_worker_module("marketplace_limits")
target_faces = category_targets.target_faces
max_bytes = marketplace_limits.max_bytes
normalize_marketplace = marketplace_limits.normalize_marketplace
size_status = marketplace_limits.size_status


def test_target_faces_by_category():
    assert target_faces("electronics") == 175_000
    assert target_faces("clothing") == 125_000
    assert target_faces("unknown_cat") == 150_000


def test_target_faces_large_tier():
    assert target_faces("clothing", tier="large") == 225_000


def test_marketplace_normalize():
    assert normalize_marketplace("wb") == "wb"
    assert normalize_marketplace("wildberries") == "wb"
    assert normalize_marketplace(None) == "ozon"


def test_marketplace_limits():
    assert max_bytes("ozon") == 15 * 1024 * 1024
    assert max_bytes("wb") == 20 * 1024 * 1024
    ozon_over = size_status(16 * 1024 * 1024, "ozon")
    assert ozon_over["warning_size_exceeded"] is True
    assert ozon_over["hard_limit_exceeded"] is True
    wb_warn = size_status(22 * 1024 * 1024, "wb")
    assert wb_warn["warning_size_exceeded"] is True
    assert wb_warn["hard_limit_exceeded"] is False
    wb_hard = size_status(26 * 1024 * 1024, "wb")
    assert wb_hard["hard_limit_exceeded"] is True


def test_skip_rate_limit_when_disabled(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_DISABLED", "1")
    assert gw_rl._skip_rate_limit() is True
    monkeypatch.delenv("RATE_LIMIT_DISABLED", raising=False)
    assert gw_rl._skip_rate_limit() is False


@pytest.mark.asyncio
async def test_check_request_skips_when_disabled(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_DISABLED", "1")

    class FakeRedis:
        async def incr(self, _key):
            raise AssertionError("redis should not be called under pytest skip")

    from starlette.requests import Request

    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "client": ("1.2.3.4", 80)}
    ok, retry, detail = await gw_rl.check_request(Request(scope), FakeRedis())
    assert ok is True
    assert retry == 0
    assert detail == ""


def test_watermark_admin_endpoints_exist():
    from app.api.v1 import watermark_admin as wa

    paths = {getattr(r, "path", "") for r in wa.router.routes}
    assert "/verify-upload" in paths
    assert "/verify-minio" in paths
