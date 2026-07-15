#!/usr/bin/env python3
"""E2E import GLB: validate → NSFW scan → Draco → thumbnail §6.10.

  python worker/scripts/e2e_import_acceptance.py --glb ./samples/model.glb
  python worker/scripts/e2e_import_acceptance.py --glb ./model.glb --category clothing

Exit: 0 ok, 1 pipeline fail
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PYTHON = sys.executable

IMPORT_PIPELINE = [
    "validate_import_glb.py",
    "scan_import_nsfw.py",
    "compress_draco.py",
    "generate_thumbnail.py",
]


def _run(step: str, task_dir: Path) -> float:
    t0 = time.monotonic()
    r = subprocess.run([PYTHON, str(SCRIPTS / step), str(task_dir)], check=False)
    dt = time.monotonic() - t0
    if r.returncode != 0:
        raise RuntimeError(f"{step} failed rc={r.returncode}")
    return dt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True, help="Path to .glb for import validation")
    ap.add_argument("--category", default="other")
    ap.add_argument("--report", default="", help="JSON report path")
    args = ap.parse_args()

    glb = Path(args.glb)
    if not glb.exists():
        print(f"GLB not found: {glb}", file=sys.stderr)
        return 1

    timings: dict[str, float] = {}
    with tempfile.TemporaryDirectory(prefix="e2e_import_") as td:
        root = Path(td)
        shutil.copy2(glb, root / "model_raw.glb")
        (root / "task_meta.json").write_text(
            json.dumps({"category": args.category, "pipeline": "import_validate"}),
            encoding="utf-8",
        )
        try:
            for step in IMPORT_PIPELINE:
                timings[step] = _run(step, root)
        except RuntimeError as exc:
            print(exc, file=sys.stderr)
            return 1

        thumb = root / "final" / "thumbnail.jpg"
        report = {
            "ok": True,
            "category": args.category,
            "glb_bytes": (root / "model.glb").stat().st_size,
            "thumbnail_bytes": thumb.stat().st_size if thumb.exists() else 0,
            "step_timings_sec": timings,
            "import_report": json.loads((root / "import_report.json").read_text(encoding="utf-8"))
            if (root / "import_report.json").exists()
            else None,
            "nsfw_report": json.loads((root / "import_nsfw_report.json").read_text(encoding="utf-8"))
            if (root / "import_nsfw_report.json").exists()
            else None,
        }
        out = args.report or str(Path(__file__).resolve().parents[1] / "e2e_reports" / "import_acceptance.json")
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
