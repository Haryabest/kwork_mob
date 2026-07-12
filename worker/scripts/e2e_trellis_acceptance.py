#!/usr/bin/env python3
"""GPU приёмка TRELLIS: полный E2E пайплайн с измерением wall-time (§1 KPI).

Бюджет:
  WORKER_DEPLOY=local → ≤180с (3 мин)
  иначе (cloud)      → ≤300с (5 мин)

Запуск на железе с весами:
  WORKER_PIPELINE_MODE=trellis \\
  python worker/scripts/e2e_trellis_acceptance.py --photos /path/to/12jpg [--fail-on-budget]

Exit codes:
  0 — успех и уложились в бюджет (или --fail-on-budget не задан)
  1 — пайплайн упал
  2 — превышен бюджет (только с --fail-on-budget)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
PYTHON = sys.executable

PIPELINE = [
    "remove_background.py",
    "trellis_generate.py",
    "retopology.py",
    "bake_pbr.py",
    "apply_watermark.py",
    "compress_draco.py",
    "validate_glb.py",
]


def _budget() -> int:
    deploy = os.getenv("WORKER_DEPLOY", "cloud").lower()
    if deploy == "local":
        return int(os.getenv("WORKER_E2E_BUDGET_LOCAL_SEC", "180"))
    return int(os.getenv("WORKER_E2E_BUDGET_SEC", "300"))


def _prepare_photos(src: Path, dest: Path) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    files = sorted(
        [p for p in src.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
        if src.is_dir()
        else []
    )
    if src.is_file():
        files = [src]
    if not files:
        raise SystemExit(f"Нет JPEG/PNG в {src}")
    for i, f in enumerate(files[:12]):
        shutil.copy2(f, dest / f"view_{i:02d}{f.suffix.lower()}")
    # добить до 12 копиями последнего (smoke) если меньше
    while len(list(dest.glob("view_*"))) < 12:
        i = len(list(dest.glob("view_*")))
        last = sorted(dest.glob("view_*"))[-1]
        shutil.copy2(last, dest / f"view_{i:02d}{last.suffix}")
    return len(list(dest.glob("view_*")))


def _run_step(name: str, task_dir: Path) -> None:
    env = os.environ.copy()
    env.setdefault("WORKER_PIPELINE_MODE", "trellis")
    env.setdefault("WORKER_FORCE_REAL_NOBG", "1")
    script = SCRIPTS / name
    r = subprocess.run(
        [PYTHON, str(script), str(task_dir)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if r.stdout:
        print(r.stdout[-800:], flush=True)
    if r.returncode != 0:
        err = (r.stderr or r.stdout or "fail")[-1500:]
        raise RuntimeError(f"{name} failed: {err}")


def main() -> int:
    parser = argparse.ArgumentParser(description="TRELLIS E2E acceptance ≤3/5 min")
    parser.add_argument("--photos", required=True, help="Директория с 12 ракурсами или одно фото")
    parser.add_argument("--workdir", default="", help="Каталог задачи (по умолчанию tempfile)")
    parser.add_argument("--fail-on-budget", action="store_true", help="Exit 2 если > бюджета")
    args = parser.parse_args()

    budget = _budget()
    photos_src = Path(args.photos)
    if args.workdir:
        task_dir = Path(args.workdir)
        task_dir.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        task_dir = Path(tempfile.mkdtemp(prefix="e2e_trellis_"))
        cleanup = True

    photos_dir = task_dir / "photos"
    n = _prepare_photos(photos_src, photos_dir)
    print(f"[e2e] photos={n} task_dir={task_dir} mode={os.getenv('WORKER_PIPELINE_MODE', 'trellis')} budget={budget}s")

    t0 = time.monotonic()
    try:
        for step in PIPELINE:
            print(f"[e2e] → {step}", flush=True)
            _run_step(step, task_dir)
        model = task_dir / "model.glb"
        if not model.exists():
            # compress/validate обычно пишут model.glb
            candidates = list(task_dir.glob("*.glb"))
            if not candidates:
                raise RuntimeError("model.glb не создан")
            model = candidates[-1]
        elapsed = time.monotonic() - t0
        size_mb = model.stat().st_size / (1024 * 1024)
        ok_budget = elapsed <= budget
        print(
            f"[e2e] DONE elapsed={elapsed:.1f}s budget={budget}s ok_budget={ok_budget} "
            f"glb={model} size_mb={size_mb:.2f}",
            flush=True,
        )
        report = task_dir / "e2e_acceptance.json"
        report.write_text(
            __import__("json").dumps(
                {
                    "elapsed_sec": round(elapsed, 2),
                    "budget_sec": budget,
                    "ok_budget": ok_budget,
                    "glb": str(model),
                    "size_mb": round(size_mb, 3),
                    "deploy": os.getenv("WORKER_DEPLOY", "cloud"),
                    "pipeline_mode": os.getenv("WORKER_PIPELINE_MODE", "trellis"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        if args.fail_on_budget and not ok_budget:
            print(f"[e2e] FAIL budget: {elapsed:.1f}s > {budget}s", file=sys.stderr)
            return 2
        return 0
    except Exception as exc:  # noqa: BLE001
        elapsed = time.monotonic() - t0
        print(f"[e2e] FAIL after {elapsed:.1f}s: {exc}", file=sys.stderr)
        return 1
    finally:
        if cleanup and os.getenv("E2E_KEEP_WORKDIR", "0") != "1":
            shutil.rmtree(task_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
