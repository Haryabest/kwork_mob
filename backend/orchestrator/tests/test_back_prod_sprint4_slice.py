"""§1.4 Sprint 4: DoD metrics, load test, TRELLIS prod."""

from __future__ import annotations

import asyncio


def test_dod_metrics_structure():
    from app.services.dod_metrics import _threshold, compute_dod_metrics

    assert _threshold("x", 1, pass_if=True)["pass"] is True

    async def _run():
        class _Scalar:
            def __init__(self, v):
                self.v = v

            def __await__(self):
                async def _():
                    return self.v

                return _().__await__()

        class _Result:
            def __init__(self, rows):
                self._rows = rows

            def all(self):
                return self._rows

        class _Db:
            async def scalar(self, *_a, **_k):
                return 0

            async def execute(self, *_a, **_k):
                return _Result([])

        async def _funnel(*_a, **_k):
            return {"funnel": {"generated": 10, "verified": 7}}

        import app.services.dod_metrics as dm

        orig = dm.funnel_svc.global_funnel
        dm.funnel_svc.global_funnel = _funnel
        try:
            out = await compute_dod_metrics(_Db(), days=7)
        finally:
            dm.funnel_svc.global_funnel = orig
        assert "checks" in out
        assert "summary" in out
        assert len(out["checks"]) >= 8

    asyncio.run(_run())


def test_load_test_concurrent_smoke():
    from app.services.load_test import run_concurrent_enqueue_smoke

    out = asyncio.run(run_concurrent_enqueue_smoke(count=20))
    assert out["tasks"] == 20


def test_admin_dod_routes():
    from app.api.v1.admin import dod_metrics, load_test_queue

    assert dod_metrics.__name__ == "dod_metrics"
    assert load_test_queue.__name__ == "load_test_queue"


def test_remove_background_deeplab_first():
    from pathlib import Path

    text = (
        Path(__file__).resolve().parents[3] / "worker" / "scripts" / "remove_background.py"
    ).read_text(encoding="utf-8")
    marker = "# §6.1.1: DeepLab primary"
    block = text[text.find(marker) : text.find(marker) + 400]
    dl_pos = block.find("_deeplab_remove")
    rem_pos = block.find("_rembg_remove")
    assert dl_pos != -1 and rem_pos != -1
    assert dl_pos < rem_pos
