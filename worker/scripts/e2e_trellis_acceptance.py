#!/usr/bin/env python3
"""GPU приёмка TRELLIS: полный E2E пайплайн с измерением wall-time (§1 KPI / §17).

Бюджет:
  WORKER_DEPLOY=local → ≤180с (3 мин)
  иначе (cloud)      → ≤300с (5 мин)

Запуск на домашнем GPU:
  WORKER_DEPLOY=local WORKER_PIPELINE_MODE=trellis TRELLIS_ALLOW_STUB_FALLBACK=0 \\
    python worker/scripts/e2e_trellis_acceptance.py --photos ./samples/dome12 \\
    --fail-on-budget --preflight

  # или фото из MinIO:
  E2E_MINIO_PREFIX=photos/<task_id>/ python worker/scripts/e2e_trellis_acceptance.py \\
    --from-minio --preflight --fail-on-budget

Exit codes:
  0 — успех и уложились в бюджет (или --fail-on-budget не задан)
  1 — пайплайн / preflight упал
  2 — превышен бюджет (только с --fail-on-budget)
  3 — preflight: нет GPU / весов / зависимостей
"""

from __future__ import annotations

import argparse
import json
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

OPTIONAL_UPSELL = [
    ("render_video_360.py", "VIDEO_360"),
    ("export_usdz_tryon.py", "USDZ_TRYON"),
]


def _cuda_info() -> dict:
    try:
        import torch

        info: dict = {
            "available": bool(torch.cuda.is_available()),
            "torch_cuda": getattr(torch.version, "cuda", None),
            "torch_version": torch.__version__,
        }
        if torch.cuda.is_available():
            cap = torch.cuda.get_device_capability(0)
            info["device"] = torch.cuda.get_device_name(0)
            info["compute_capability"] = f"sm_{cap[0]}{cap[1]}"
        return info
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "error": str(exc)[:200]}


def _budget() -> int:
    deploy = os.getenv("WORKER_DEPLOY", "cloud").lower()
    if deploy == "local":
        return int(os.getenv("WORKER_E2E_BUDGET_LOCAL_SEC", "180"))
    return int(os.getenv("WORKER_E2E_BUDGET_SEC", "300"))


def _gpu_profile(cuda: dict) -> str:
    """Профиль GPU для отчёта приёмки (RTX 5070 = sm_120)."""
    cc = cuda.get("compute_capability") or ""
    device = (cuda.get("device") or "").lower()
    if cc == "sm_120" or "5070" in device:
        return "rtx_5070_blackwell"
    if cc in ("sm_89", "sm_90"):
        return "ada_hopper"
    if cuda.get("available"):
        return "cuda_generic"
    return "cpu"


def _preflight(*, require_gpu: bool) -> list[str]:
    """Проверки железа/зависимостей до пайплайна. Возвращает список ошибок."""
    errors: list[str] = []

    # CUDA + TRELLIS.2 preflight
    try:
        import torch

        if require_gpu and not torch.cuda.is_available():
            errors.append("CUDA недоступна (torch.cuda.is_available()=False)")
        elif torch.cuda.is_available():
            cuda = _cuda_info()
            print(
                f"[preflight] GPU: {cuda.get('device')} {cuda.get('compute_capability')} "
                f"torch.cuda={cuda.get('torch_cuda')}",
                flush=True,
            )
            if os.getenv("TRELLIS_VERSION", "2").lower() in ("2", "trellis2", "trellis.2"):
                sys.path.insert(0, str(SCRIPTS))
                from trellis_runtime import preflight_cuda

                try:
                    preflight_cuda()
                except Exception as exc:  # noqa: BLE001
                    errors.append(str(exc))
    except Exception as exc:  # noqa: BLE001
        if require_gpu:
            errors.append(f"torch: {exc}")

    mode = os.getenv("WORKER_PIPELINE_MODE", "trellis").lower()
    if mode != "trellis" and require_gpu:
        errors.append(f"WORKER_PIPELINE_MODE={mode} (нужен trellis)")

    weights = Path(os.getenv("TRELLIS_WEIGHTS", str(ROOT / "trellis" / "weights")))
    trellis_root = Path(os.getenv("TRELLIS_ROOT", str(ROOT / "trellis")))
    if require_gpu:
        if not trellis_root.exists():
            errors.append(f"TRELLIS_ROOT отсутствует: {trellis_root}")
        ver = os.getenv("TRELLIS_VERSION", "2").lower()
        if ver in ("2", "trellis2", "trellis.2"):
            print(f"[preflight] TRELLIS.2 weights={weights}", flush=True)
        elif not (weights.exists() and any(weights.rglob("*"))):
            errors.append(f"TRELLIS_WEIGHTS пуст/нет: {weights}")

    blender = os.getenv("BLENDER_BIN") or shutil.which("blender")
    if not blender:
        print("[preflight] WARN: blender не найден — bake/video_360 fallback", flush=True)
    else:
        print(f"[preflight] blender={blender}", flush=True)

    im = os.getenv("INSTANT_MESHES_BIN") or shutil.which("instant_meshes")
    if not im:
        print("[preflight] WARN: instant_meshes не найден — Open3D fallback", flush=True)
    else:
        print(f"[preflight] instant_meshes={im}", flush=True)

    for name in PIPELINE:
        if not (SCRIPTS / name).exists():
            errors.append(f"нет скрипта {name}")

    return errors


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
    while len(list(dest.glob("view_*"))) < 12:
        i = len(list(dest.glob("view_*")))
        last = sorted(dest.glob("view_*"))[-1]
        shutil.copy2(last, dest / f"view_{i:02d}{last.suffix}")
    return len(list(dest.glob("view_*")))


def _download_photos_minio(dest: Path) -> int:
    """Скачать view_* из MinIO (§5.4 — photos_url / prefix)."""
    import boto3
    from botocore.client import Config

    bucket = os.getenv("E2E_MINIO_BUCKET", os.getenv("MINIO_BUCKET_PHOTOS", "photos"))
    prefix = os.getenv("E2E_MINIO_PREFIX", "").strip()
    if not prefix:
        raise SystemExit("--from-minio требует E2E_MINIO_PREFIX (например photos/order-uuid/)")

    client = boto3.client(
        "s3",
        endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents") or []:
            key = obj["Key"]
            if key.endswith("/"):
                continue
            name = Path(key).name
            if not name.lower().startswith("view_"):
                continue
            if Path(name).suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
                continue
            client.download_file(bucket, key, str(dest / name))
            count += 1
            print(f"[e2e] minio s3://{bucket}/{key}", flush=True)
    if count == 0:
        raise SystemExit(f"Нет view_* в s3://{bucket}/{prefix}")
    return count


def _persist_report(task_report_path: Path, report: dict) -> None:
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    task_report_path.write_text(payload, encoding="utf-8")
    out_dir = Path(os.getenv("E2E_REPORT_DIR", str(ROOT / "e2e_reports")))
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (out_dir / f"acceptance_{stamp}.json").write_text(payload, encoding="utf-8")


def _run_step(name: str, task_dir: Path) -> dict:
    env = os.environ.copy()
    env.setdefault("WORKER_PIPELINE_MODE", "trellis")
    env.setdefault("TRELLIS_VERSION", "2")
    env.setdefault("TRELLIS_WEIGHTS", "microsoft/TRELLIS.2-4B")
    env.setdefault("TRELLIS2_PIPELINE_TYPE", "512")
    env.setdefault("TRELLIS2_LOW_VRAM", "1")
    env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    env.setdefault("ATTN_BACKEND", "xformers")
    env.setdefault("WORKER_FORCE_REAL_NOBG", "1")
    env.setdefault("TRELLIS_ALLOW_STUB_FALLBACK", "0")
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(SCRIPTS), env.get("PYTHONPATH", "")) if p
    )
    script = SCRIPTS / name
    t0 = time.monotonic()
    r = subprocess.run(
        [PYTHON, str(script), str(task_dir)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    dt = time.monotonic() - t0
    if r.stdout:
        print(r.stdout[-800:], flush=True)
    if r.returncode != 0:
        err = (r.stderr or r.stdout or "fail")[-1500:]
        raise RuntimeError(f"{name} failed ({dt:.1f}s): {err}")
    return {"step": name, "sec": round(dt, 2), "ok": True}


def main() -> int:
    parser = argparse.ArgumentParser(description="TRELLIS E2E acceptance ≤3/5 min")
    parser.add_argument(
        "--photos",
        default="",
        help="Директория с 12 ракурсами или одно фото (не нужно с --from-minio)",
    )
    parser.add_argument(
        "--from-minio",
        action="store_true",
        help="Скачать view_* из MinIO (E2E_MINIO_BUCKET, E2E_MINIO_PREFIX)",
    )
    parser.add_argument("--workdir", default="", help="Каталог задачи (по умолчанию tempfile)")
    parser.add_argument("--fail-on-budget", action="store_true", help="Exit 2 если > бюджета")
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Проверить CUDA/веса/скрипты до запуска (exit 3 при ошибке)",
    )
    parser.add_argument(
        "--allow-no-gpu",
        action="store_true",
        help="Не требовать CUDA в preflight (только для отладки оркестрации)",
    )
    parser.add_argument(
        "--with-upsells",
        action="store_true",
        help="После validate: video_360 + usdz (не входит в KPI-бюджет wall-time)",
    )
    args = parser.parse_args()

    if not args.from_minio and not args.photos:
        parser.error("укажите --photos <dir> или --from-minio")

    if args.preflight or not args.allow_no_gpu:
        # preflight по умолчанию при --fail-on-budget
        do_pf = args.preflight or args.fail_on_budget
        if do_pf:
            errs = _preflight(require_gpu=not args.allow_no_gpu)
            if errs:
                for e in errs:
                    print(f"[preflight] FAIL: {e}", file=sys.stderr)
                return 3
            print("[preflight] OK", flush=True)

    budget = _budget()
    photos_src = Path(args.photos) if args.photos else None
    if args.workdir:
        task_dir = Path(args.workdir)
        task_dir.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        task_dir = Path(tempfile.mkdtemp(prefix="e2e_trellis_"))
        cleanup = True

    # meta для watermark / bake category
    meta = {
        "user_id": int(os.getenv("TASK_USER_ID", "1")),
        "company_id": int(os.getenv("TASK_COMPANY_ID", "0") or 0),
        "order_id": int(os.getenv("TASK_ORDER_ID", "1")),
        "category": os.getenv("TASK_CATEGORY", "electronics"),
        "timestamp": int(time.time()),
    }
    (task_dir / "task_meta.json").write_text(json.dumps(meta), encoding="utf-8")

    photos_dir = task_dir / "photos"
    if args.from_minio:
        n = _download_photos_minio(photos_dir)
    else:
        n = _prepare_photos(photos_src, photos_dir)
    print(
        f"[e2e] photos={n} task_dir={task_dir} mode={os.getenv('WORKER_PIPELINE_MODE', 'trellis')} "
        f"deploy={os.getenv('WORKER_DEPLOY', 'cloud')} budget={budget}s",
        flush=True,
    )

    steps: list[dict] = []
    t0 = time.monotonic()
    try:
        for step in PIPELINE:
            print(f"[e2e] → {step}", flush=True)
            steps.append(_run_step(step, task_dir))
        model = task_dir / "model.glb"
        if not model.exists():
            candidates = list(task_dir.glob("*.glb"))
            if not candidates:
                raise RuntimeError("model.glb не создан")
            model = max(candidates, key=lambda p: p.stat().st_mtime)
            if model.name != "model.glb":
                shutil.copy2(model, task_dir / "model.glb")
                model = task_dir / "model.glb"
        elapsed = time.monotonic() - t0
        size_mb = model.stat().st_size / (1024 * 1024)
        ok_budget = elapsed <= budget

        upsell_info: list[dict] = []
        if args.with_upsells:
            for script, flag in OPTIONAL_UPSELL:
                if not (SCRIPTS / script).exists():
                    continue
                print(f"[e2e] upsell → {script}", flush=True)
                try:
                    upsell_info.append(_run_step(script, task_dir))
                except Exception as exc:  # noqa: BLE001
                    upsell_info.append({"step": script, "ok": False, "error": str(exc)[:400]})

        print(
            f"[e2e] DONE elapsed={elapsed:.1f}s budget={budget}s ok_budget={ok_budget} "
            f"glb={model} size_mb={size_mb:.2f}",
            flush=True,
        )
        report = {
            "elapsed_sec": round(elapsed, 2),
            "budget_sec": budget,
            "ok_budget": ok_budget,
            "glb": str(model),
            "size_mb": round(size_mb, 3),
            "deploy": os.getenv("WORKER_DEPLOY", "cloud"),
            "pipeline_mode": os.getenv("WORKER_PIPELINE_MODE", "trellis"),
            "trellis_version": os.getenv("TRELLIS_VERSION", "2"),
            "trellis2_pipeline_type": os.getenv("TRELLIS2_PIPELINE_TYPE", "512"),
            "cuda": _cuda_info(),
            "gpu_profile": _gpu_profile(_cuda_info()),
            "steps": steps,
            "step_timings": {s["step"]: s["sec"] for s in steps},
            "upsells": upsell_info,
            "meta": meta,
        }
        _persist_report(task_dir / "e2e_acceptance.json", report)

        if args.fail_on_budget and not ok_budget:
            print(f"[e2e] FAIL budget: {elapsed:.1f}s > {budget}s", file=sys.stderr)
            return 2
        return 0
    except Exception as exc:  # noqa: BLE001
        elapsed = time.monotonic() - t0
        print(f"[e2e] FAIL after {elapsed:.1f}s: {exc}", file=sys.stderr)
        fail_report = {
            "elapsed_sec": round(elapsed, 2),
            "budget_sec": budget,
            "ok_budget": False,
            "error": str(exc)[:2000],
            "trellis_version": os.getenv("TRELLIS_VERSION", "2"),
            "cuda": _cuda_info(),
            "steps": steps,
            "step_timings": {s["step"]: s["sec"] for s in steps},
        }
        try:
            _persist_report(task_dir / "e2e_acceptance.json", fail_report)
        except Exception:  # noqa: BLE001
            pass
        return 1
    finally:
        if cleanup and os.getenv("E2E_KEEP_WORKDIR", "0") != "1":
            shutil.rmtree(task_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
