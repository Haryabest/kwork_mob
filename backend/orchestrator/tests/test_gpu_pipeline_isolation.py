"""GPU pipeline: subprocess steps + skip internal TRELLIS rembg."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

WORKER_SCRIPTS = Path(__file__).resolve().parents[3] / "worker" / "scripts"


def _load_trellis_runtime():
    path = WORKER_SCRIPTS / "trellis_runtime.py"
    spec = importlib.util.spec_from_file_location("trellis_runtime", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["trellis_runtime"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_skip_internal_rembg_default_on():
    tr = _load_trellis_runtime()
    assert tr._skip_internal_rembg() is True


def test_drop_internal_rembg_clears_model():
    tr = _load_trellis_runtime()
    pipe = MagicMock()
    rembg = MagicMock()
    pipe.rembg_model = rembg
    pipe.models = {"rembg": rembg}
    with patch.object(tr, "_free_cuda_memory") as free:
        tr._drop_internal_rembg(pipe)
    assert pipe.rembg_model is None
    rembg.cpu.assert_called_once()
    free.assert_called_once()


def test_worker_trellis_subprocess_default():
    path = Path(__file__).resolve().parents[3] / "worker" / "worker_agent.py"
    text = path.read_text(encoding="utf-8")
    assert 'WORKER_TRELLIS_INPROCESS", "0")' in text
