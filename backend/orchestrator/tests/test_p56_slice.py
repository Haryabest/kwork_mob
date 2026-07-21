"""§5.4 source insurance, §5.5 worker idempotency helpers, §5.6 corp texture size."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _texture_size_for_meta(meta: dict) -> int:
    company_id = int(meta.get("company_id") or 0)
    tier = str(meta.get("tier") or "").lower()
    if company_id > 0 or tier == "large":
        return 2048
    return 1024


def test_texture_size_for_meta_corp():
    assert _texture_size_for_meta({"company_id": 10, "tier": "small"}) == 2048
    assert _texture_size_for_meta({"company_id": 0, "tier": "large"}) == 2048
    assert _texture_size_for_meta({"company_id": 0, "tier": "small"}) == 1024


def test_store_insurance_copy_keys():
    from app.services.source_insurance import store_insurance_copy

    with patch("app.services.source_insurance.minio_service") as m:
        m.object_exists.return_value = True
        m.download_bytes.return_value = b"zip"
        m.upload_bytes.return_value = "s3://backups/x"
        out = store_insurance_copy(
            task_uuid="task-1",
            user_id=5,
            company_id=9,
            zip_key="photos/task-1/source.zip",
        )
    assert out["ok"] is True
    assert any("backups/5/task-1" in k for k in out["keys"])
    assert any("company_9" in k for k in out["keys"])


@pytest.fixture
def worker_agent_mod():
    for name in ("psutil", "redis", "boto3"):
        sys.modules.setdefault(name, MagicMock())
    worker_root = Path(__file__).resolve().parents[3] / "worker"
    sys.path.insert(0, str(worker_root))
    import worker_agent as wa  # noqa: WPS433

    return wa


def test_existing_model_key(worker_agent_mod):
    agent = worker_agent_mod.WorkerAgent.__new__(worker_agent_mod.WorkerAgent)
    agent.minio = MagicMock()
    agent.minio.head_object.return_value = {}
    key = agent._existing_model_key("abc", "models")
    assert key == "models/abc/model.glb"
