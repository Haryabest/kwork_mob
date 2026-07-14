"""
Агент GPU-воркера (production).
WS → Redlock → MinIO download → пайплайн + чекпоинты → MinIO upload.
Overheat / grace: stop + requeue с checkpoint_path.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import boto3
import psutil
import redis
import websockets
from botocore.client import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("worker_agent")

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_WS_URL", "ws://localhost:8000/ws/worker")
WORKER_ID = os.getenv("WORKER_ID", "worker-1")
WORKER_TOKEN = os.getenv("WORKER_TOKEN", "worker-dev-token")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
TEMP_DIR = Path(os.getenv("TEMP_DIR", "/tmp/worker"))
PIPELINE_MODE = os.getenv("WORKER_PIPELINE_MODE", "trellis")  # trellis | stub
WATERMARK_SECRET = os.getenv("WATERMARK_HMAC_SECRET", "change-me-watermark")


def _resolve_scripts_dir() -> Path:
    """Путь к scripts/: рядом с агентом или /app/scripts в Docker."""
    if env := os.getenv("WORKER_SCRIPTS_DIR"):
        return Path(env)
    here = Path(__file__).resolve().parent
    for candidate in (here / "scripts", Path("/app/scripts")):
        if candidate.is_dir():
            return candidate
    return here / "scripts"


SCRIPTS_DIR = _resolve_scripts_dir()
PYTHON = sys.executable
CHECKPOINTS_BUCKET = os.getenv("MINIO_BUCKET_CHECKPOINTS", "backups")
E2E_BUDGET_SEC = int(os.getenv("WORKER_E2E_BUDGET_SEC", "300"))  # облако ≤5 мин
E2E_BUDGET_LOCAL_SEC = int(os.getenv("WORKER_E2E_BUDGET_LOCAL_SEC", "180"))  # ПК ≤3 мин
WS_FALLBACK_URL = os.getenv("ORCHESTRATOR_WS_FALLBACK_URL", "")
WS_CONNECT_TIMEOUT = float(os.getenv("WORKER_WS_CONNECT_TIMEOUT", "10"))
TASK_DRAIN_TIMEOUT_SEC = int(os.getenv("WORKER_TASK_DRAIN_TIMEOUT_SEC", "3600"))
SUBPROCESS_STREAM = os.getenv("WORKER_SUBPROCESS_STREAM", "1").lower() in ("1", "true", "yes")

PIPELINE_STEPS = [
    "remove_background.py",
    "trellis_generate.py",
    "retopology.py",
    "bake_pbr.py",
    "apply_watermark.py",
    "compress_draco.py",
    "validate_glb.py",
]

# апсейлы §17 — hole_filling после retopology (на retopo.glb); остальные после validate
UPSELL_AFTER_RETOPO = {"hole_filling": "apply_hole_filling.py"}
UPSELL_AFTER_VALIDATE = {
    "real_scale": "apply_real_scale.py",
    "video_360": "render_video_360.py",
    "virtual_tryon": "export_usdz_tryon.py",
}


def _orchestrator_http_base() -> str:
    if u := os.getenv("ORCHESTRATOR_HTTP_URL", "").strip():
        return u.rstrip("/")
    base = ORCHESTRATOR_URL.replace("wss://", "https://").replace("ws://", "http://")
    for sep in ("/ws/worker", "/ws/"):
        if sep in base:
            return base.split(sep)[0].rstrip("/")
    return base.rstrip("/")


def build_pipeline(upsell_options: list | None) -> list[str]:
    opts = set(upsell_options or [])
    steps = list(PIPELINE_STEPS)
    # hole_filling после retopology
    if "hole_filling" in opts:
        idx = steps.index("retopology.py") + 1
        steps.insert(idx, UPSELL_AFTER_RETOPO["hole_filling"])
    for code, script in UPSELL_AFTER_VALIDATE.items():
        if code in opts:
            steps.append(script)
    return steps


class WorkerAgent:
    def __init__(self) -> None:
        self.worker_id = WORKER_ID
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        self.minio = boto3.client(
            "s3",
            endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        self.temp_dir = TEMP_DIR
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.current_task: str | None = None
        self.status = "idle"
        self._stop_task = False
        self._overheated = False
        self._task_coro: asyncio.Task | None = None
        self._ws = None
        self.config = {
            "quality_threshold": float(os.getenv("QUALITY_THRESHOLD", "0.7")),
            "temp_threshold_high": 85,
            "temp_threshold_low": 75,
            "dwt_watermark_strength": 0.01,
        }

    def acquire_lock(self, task_id: str) -> bool:
        key = f"task:{task_id}"
        owner = self.redis_client.get(key)
        if owner == self.worker_id:
            self.redis_client.expire(key, 120)
            return True
        if owner is None:
            return bool(self.redis_client.set(key, self.worker_id, nx=True, ex=120))
        return False

    def renew_lock(self, task_id: str) -> None:
        owner = self.redis_client.get(f"task:{task_id}")
        if owner == self.worker_id:
            self.redis_client.expire(f"task:{task_id}", 120)

    def release_lock(self, task_id: str) -> None:
        owner = self.redis_client.get(f"task:{task_id}")
        if owner == self.worker_id:
            self.redis_client.delete(f"task:{task_id}")

    def get_gpu_metrics(self) -> dict:
        try:
            import pynvml

            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode()
            return {
                "name": name,
                "gpu_util": util.gpu,
                "vram_used_gb": round(mem.used / 1e9, 2),
                "vram_total_gb": round(mem.total / 1e9, 2),
                "gpu_temp": temp,
            }
        except Exception:  # noqa: BLE001
            # CPU / тест: WORKER_FAKE_GPU_TEMP для проверки overheat
            fake = os.getenv("WORKER_FAKE_GPU_TEMP")
            temp = int(fake) if fake else 0
            return {
                "gpu_util": 0,
                "vram_used_gb": 0,
                "vram_total_gb": 0,
                "gpu_temp": temp,
                "name": "cpu",
            }

    def download_photos(self, bucket: str, prefix: str, dest: Path) -> int:
        dest.mkdir(parents=True, exist_ok=True)
        count = 0
        paginator = self.minio.get_paginator("list_objects_v2")
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
                local = dest / name
                self.minio.download_file(bucket, key, str(local))
                count += 1
                logger.info("Downloaded s3://%s/%s", bucket, key)
        return count

    def upload_model(self, bucket: str, key: str, local_path: Path) -> str:
        self.minio.upload_file(
            str(local_path),
            bucket,
            key,
            ExtraArgs={"ContentType": "model/gltf-binary"},
        )
        return f"s3://{bucket}/{key}"

    def _checkpoint_key(self, task_id: str) -> str:
        return f"checkpoints/{task_id}/checkpoint.json"

    def save_checkpoint(self, task_dir: Path, task_id: str, completed_steps: list[str]) -> str:
        meta = {
            "task_id": task_id,
            "completed_steps": completed_steps,
            "stage": completed_steps[-1] if completed_steps else None,
            "progress": round(100.0 * len(completed_steps) / max(len(PIPELINE_STEPS), 1), 1),
            "updated_at": time.time(),
            "worker_id": self.worker_id,
        }
        path = task_dir / "checkpoint.json"
        path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        key = self._checkpoint_key(task_id)
        # архив артефактов этапа
        for name in ("photos_nobg", "raw_mesh.glb", "model.glb", "watermark.hmac"):
            p = task_dir / name
            if p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        rel = f.relative_to(task_dir).as_posix()
                        self.minio.upload_file(str(f), CHECKPOINTS_BUCKET, f"checkpoints/{task_id}/{rel}")
            elif p.is_file():
                self.minio.upload_file(str(p), CHECKPOINTS_BUCKET, f"checkpoints/{task_id}/{name}")
        self.minio.upload_file(str(path), CHECKPOINTS_BUCKET, key)
        return f"s3://{CHECKPOINTS_BUCKET}/{key}"

    def load_checkpoint(self, task_dir: Path, checkpoint_path: str | None, task_id: str) -> list[str]:
        if not checkpoint_path and not self._remote_checkpoint_exists(task_id):
            return []
        key = self._checkpoint_key(task_id)
        try:
            local = task_dir / "checkpoint.json"
            self.minio.download_file(CHECKPOINTS_BUCKET, key, str(local))
            meta = json.loads(local.read_text(encoding="utf-8"))
            # скачать артефакты
            prefix = f"checkpoints/{task_id}/"
            paginator = self.minio.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=CHECKPOINTS_BUCKET, Prefix=prefix):
                for obj in page.get("Contents") or []:
                    k = obj["Key"]
                    if k.endswith("checkpoint.json"):
                        continue
                    rel = k[len(prefix) :]
                    dest = task_dir / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    self.minio.download_file(CHECKPOINTS_BUCKET, k, str(dest))
            return list(meta.get("completed_steps") or [])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Checkpoint load failed: %s", exc)
            return []

    def _remote_checkpoint_exists(self, task_id: str) -> bool:
        try:
            self.minio.head_object(Bucket=CHECKPOINTS_BUCKET, Key=self._checkpoint_key(task_id))
            return True
        except Exception:  # noqa: BLE001
            return False

    def _run_script_stream(self, name: str, script: Path, task_dir: Path, env: dict) -> None:
        process = subprocess.Popen(
            [PYTHON, str(script), str(task_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        assert process.stdout is not None
        for line in process.stdout:
            line = line.rstrip("\n\r")
            if line:
                logger.info("[%s] %s", name, line)
        rc = process.wait()
        if rc != 0:
            raise RuntimeError(f"{name} failed ({rc})")

    def run_script(self, name: str, task_dir: Path) -> None:
        script = SCRIPTS_DIR / name
        env = os.environ.copy()
        env["WORKER_PIPELINE_MODE"] = PIPELINE_MODE
        env["WATERMARK_HMAC_SECRET"] = WATERMARK_SECRET
        env["PYTHONPATH"] = os.pathsep.join(
            p for p in (str(SCRIPTS_DIR), env.get("PYTHONPATH", "")) if p
        )
        # для E2E без GPU: реальное удаление фона даже в stub, если включено
        if name == "remove_background.py" and os.getenv("WORKER_REAL_NOBG", "1") in ("1", "true", "yes"):
            env["WORKER_FORCE_REAL_NOBG"] = "1"
        meta_path = task_dir / "task_meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                env["TASK_USER_ID"] = str(meta.get("user_id") or 0)
                env["TASK_ORDER_ID"] = str(meta.get("order_id") or 0)
                env["TASK_COMPANY_ID"] = str(meta.get("company_id") or 0)
            except Exception:  # noqa: BLE001
                pass
        t0 = time.monotonic()
        logger.info("Starting step %s", name)
        if SUBPROCESS_STREAM:
            self._run_script_stream(name, script, task_dir, env)
        else:
            result = subprocess.run(
                [PYTHON, str(script), str(task_dir)],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
            if result.stdout:
                logger.info("[%s] %s", name, result.stdout.strip()[-500:])
            if result.returncode != 0:
                err = (result.stderr or result.stdout or "script failed")[-1000:]
                raise RuntimeError(f"{name} failed ({result.returncode}): {err}")
        logger.info("Finished step %s in %.1fs", name, time.monotonic() - t0)

    async def _notify_event(self, payload: dict) -> None:
        payload = {**payload, "worker_id": self.worker_id}
        ws = self._ws
        if ws is not None:
            try:
                await ws.send(json.dumps(payload))
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("WS notify failed (%s), HTTP fallback", exc)
        import httpx

        url = f"{_orchestrator_http_base()}/api/v1/worker/event"
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {WORKER_TOKEN}"},
            )
            if r.status_code >= 400:
                logger.error("HTTP notify failed %s: %s", r.status_code, r.text[:500])
                r.raise_for_status()
        logger.info("HTTP notify ok: %s task=%s", payload.get("type"), payload.get("task_id"))

    async def start_task(self, task_id: str, payload: dict, ws) -> None:
        if self._overheated:
            await self._notify_event(
                {
                    "type": "task_conflict",
                    "task_id": task_id,
                    "reason": "overheated",
                }
            )
            return

        if not self.acquire_lock(task_id):
            await self._notify_event({"type": "task_conflict", "task_id": task_id})
            return

        self.current_task = task_id
        self.status = "processing"
        self._stop_task = False
        task_dir = self.temp_dir / task_id
        checkpoint_path = payload.get("checkpoint_path")
        resume = bool(checkpoint_path) or self._remote_checkpoint_exists(task_id)

        if task_dir.exists() and not resume:
            shutil.rmtree(task_dir, ignore_errors=True)
        task_dir.mkdir(parents=True, exist_ok=True)
        photos_dir = task_dir / "photos"

        completed: list[str] = []
        try:
            await self._notify_event({"type": "task_started", "task_id": task_id})
            self.renew_lock(task_id)

            if resume:
                completed = await asyncio.to_thread(
                    self.load_checkpoint, task_dir, checkpoint_path, task_id
                )
                logger.info("Resume task %s from steps=%s", task_id, completed)

            if not (photos_dir.exists() and any(photos_dir.iterdir())):
                bucket = payload.get("photos_bucket") or "photos"
                prefix = payload.get("photos_prefix") or f"photos/{task_id}/"
                n = await asyncio.to_thread(self.download_photos, bucket, prefix, photos_dir)
                if n == 0:
                    raise RuntimeError(
                        f"Нет фото в s3://{bucket}/{prefix} — загрузите 12 ракурсов (view_00…view_11.jpg)"
                    )
                enc_key = payload.get("photo_encryption_key")
                if enc_key:
                    scripts = Path(__file__).resolve().parent / "scripts"
                    sys.path.insert(0, str(scripts))
                    from photo_decrypt import decrypt_photos_dir

                    dec = await asyncio.to_thread(decrypt_photos_dir, photos_dir, enc_key)
                    logger.info("Decrypted %s encrypted photos in RAM/temp (§10.6.2)", dec)

            meta = {
                "task_id": task_id,
                "user_id": payload.get("user_id"),
                "order_id": payload.get("order_id"),
                "company_id": payload.get("company_id"),
                "category": payload.get("category"),
                "upsell_options": payload.get("upsell_options") or [],
                "scale_calibration": payload.get("scale_calibration"),
                "trellis_version": os.getenv("TRELLIS_VERSION", "2"),
                "trellis2_pipeline_type": os.getenv("TRELLIS2_PIPELINE_TYPE", "512"),
            }
            (task_dir / "task_meta.json").write_text(
                json.dumps(meta, ensure_ascii=False), encoding="utf-8"
            )

            models_bucket = payload.get("models_bucket") or "models"
            pipeline = build_pipeline(payload.get("upsell_options"))
            t0 = time.monotonic()

            for step in pipeline:
                if self._stop_task or self._overheated:
                    cp = await asyncio.to_thread(self.save_checkpoint, task_dir, task_id, completed)
                    await self._notify_event(
                        {
                            "type": "task_paused",
                            "task_id": task_id,
                            "checkpoint_path": cp,
                            "reason": "overheat" if self._overheated else "stop",
                            "completed_steps": completed,
                        }
                    )
                    return
                if step in completed:
                    continue
                self.renew_lock(task_id)
                await asyncio.to_thread(self.run_script, step, task_dir)
                completed.append(step)
                await asyncio.to_thread(self.save_checkpoint, task_dir, task_id, completed)
                if step == "remove_background.py":
                    seg = {}
                    meta_path = task_dir / "task_meta.json"
                    if meta_path.exists():
                        try:
                            seg = json.loads(meta_path.read_text(encoding="utf-8")).get("segmentation") or {}
                        except Exception:  # noqa: BLE001
                            seg = {}
                    frames = seg.get("frames") or []
                    methods = [str(f.get("method") or "") for f in frames if isinstance(f, dict)]
                    await self._notify_event(
                        {
                            "type": "segmentation_stats",
                            "task_id": task_id,
                            "device_model": payload.get("device_model"),
                            "os_version": payload.get("os_version"),
                            "segmentation": {
                                **seg,
                                "fallback_used": any(m == "sam" for m in methods),
                                "failed": False,
                            },
                        }
                    )

            model_path = task_dir / "model.glb"
            if not model_path.exists():
                raise RuntimeError("model.glb missing after pipeline")

            glb_key = f"models/{task_id}/model.glb"
            result_url = await asyncio.to_thread(self.upload_model, models_bucket, glb_key, model_path)
            extras_urls: dict[str, str] = {}
            usdz_path = task_dir / "model.usdz"
            if usdz_path.exists():
                extras_urls["usdz_url"] = await asyncio.to_thread(
                    self.upload_model, models_bucket, f"models/{task_id}/model.usdz", usdz_path
                )
            video_path = task_dir / "video_360.mp4"
            if video_path.exists():
                extras_urls["video_360_url"] = await asyncio.to_thread(
                    self.upload_model, models_bucket, f"models/{task_id}/video_360.mp4", video_path
                )
            hmac_path = task_dir / "watermark.hmac"
            watermark_hmac = hmac_path.read_text(encoding="utf-8").strip() if hmac_path.exists() else None
            if not watermark_hmac:
                digest = hmac.new(
                    WATERMARK_SECRET.encode(),
                    model_path.read_bytes(),
                    hashlib.sha256,
                ).hexdigest()
                watermark_hmac = digest

            quality_score = None
            qpath = task_dir / "quality_report.json"
            if qpath.exists():
                try:
                    quality_score = float(json.loads(qpath.read_text(encoding="utf-8")).get("quality_score"))
                except Exception:  # noqa: BLE001
                    quality_score = None
            threshold = float(self.config.get("quality_threshold", 0.7))
            if quality_score is not None and quality_score < threshold:
                raise RuntimeError(
                    f"quality_gate_failed score={quality_score} < {threshold}"
                )

            seg_payload = {}
            meta_path = task_dir / "task_meta.json"
            if meta_path.exists():
                try:
                    seg_payload = json.loads(meta_path.read_text(encoding="utf-8")).get("segmentation") or {}
                except Exception:  # noqa: BLE001
                    seg_payload = {}

            await self._notify_event(
                {
                    "type": "task_completed",
                    "task_id": task_id,
                    "result_url": result_url,
                    "glb_url": result_url,
                    "usdz_url": extras_urls.get("usdz_url"),
                    "video_360_url": extras_urls.get("video_360_url"),
                    "watermark_hmac": watermark_hmac,
                    "quality_score": quality_score,
                    "upsell_options": payload.get("upsell_options") or [],
                    "elapsed_sec": round(time.monotonic() - t0, 2),
                    "e2e_budget_sec": E2E_BUDGET_SEC,
                    "device_model": payload.get("device_model"),
                    "os_version": payload.get("os_version"),
                    "segmentation": seg_payload,
                }
            )
            elapsed = time.monotonic() - t0
            budget = E2E_BUDGET_LOCAL_SEC if os.getenv("WORKER_DEPLOY", "cloud") == "local" else E2E_BUDGET_SEC
            if elapsed > budget:
                logger.warning("Task %s exceeded E2E budget: %.1fs > %ss", task_id, elapsed, budget)
            logger.info("Task %s completed in %.1fs (budget %ss) → %s", task_id, elapsed, budget, result_url)
            shutil.rmtree(task_dir, ignore_errors=True)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Task %s failed", task_id)
            try:
                cp = await asyncio.to_thread(self.save_checkpoint, task_dir, task_id, completed)
            except Exception:  # noqa: BLE001
                cp = None
            await self._notify_event(
                {
                    "type": "task_failed",
                    "task_id": task_id,
                    "error": str(exc),
                    "checkpoint_path": cp,
                    "device_model": payload.get("device_model"),
                    "os_version": payload.get("os_version"),
                    "segmentation": (
                        json.loads((task_dir / "task_meta.json").read_text(encoding="utf-8")).get(
                            "segmentation"
                        )
                        if (task_dir / "task_meta.json").exists()
                        else None
                    ),
                }
            )
        finally:
            self.release_lock(task_id)
            self.current_task = None
            if not self._overheated:
                self.status = "idle"

    async def handle_message(self, message: str, ws) -> None:
        data = json.loads(message)
        msg_type = data.get("type")

        if msg_type == "task":
            task_id = data["task_id"]
            if (
                self.current_task == task_id
                and self._task_coro is not None
                and not self._task_coro.done()
            ):
                logger.info("Already processing task %s, skip duplicate assign", task_id)
                return
            self._task_coro = asyncio.create_task(
                self.start_task(task_id, data.get("payload") or {}, ws)
            )
        elif msg_type == "stop":
            self._stop_task = True
            self.status = "idle"
        elif msg_type == "config_update":
            self.config.update(data.get("settings") or {})
        elif msg_type in ("ack", "registered", "pong"):
            pass
        else:
            logger.debug("Unhandled message: %s", msg_type)

    async def send_heartbeat(self, ws) -> None:
        while True:
            await ws.send(
                json.dumps(
                    {
                        "type": "heartbeat",
                        "worker_id": self.worker_id,
                        "status": self.status,
                    }
                )
            )
            await asyncio.sleep(5)

    async def send_metrics(self, ws) -> None:
        while True:
            gpu = self.get_gpu_metrics()
            temp = int(gpu.get("gpu_temp") or 0)
            high = int(self.config.get("temp_threshold_high") or 85)
            low = int(self.config.get("temp_threshold_low") or 75)

            if temp >= high and not self._overheated:
                self._overheated = True
                self._stop_task = True
                self.status = "overheated"
                await ws.send(
                    json.dumps(
                        {
                            "type": "overheating",
                            "worker_id": self.worker_id,
                            "temp": temp,
                            "task_id": self.current_task,
                        }
                    )
                )
                logger.warning("GPU overheat %s°C — pausing", temp)
            elif self._overheated and temp <= low:
                self._overheated = False
                self._stop_task = False
                self.status = "idle"
                await ws.send(
                    json.dumps(
                        {
                            "type": "ready",
                            "worker_id": self.worker_id,
                            "version": "0.4.0",
                            "capabilities": self._capabilities(),
                            "weight": float(os.getenv("WORKER_WEIGHT", "0")),
                            "pipeline_mode": PIPELINE_MODE,
                        }
                    )
                )
                logger.info("GPU cooled to %s°C — ready", temp)

            await ws.send(
                json.dumps(
                    {
                        "type": "metrics",
                        "worker_id": self.worker_id,
                        "gpu": gpu,
                        "cpu_percent": psutil.cpu_percent(),
                        "ram_percent": psutil.virtual_memory().percent,
                        "status": self.status,
                    }
                )
            )
            await asyncio.sleep(5)

    def _capabilities(self) -> list[str]:
        caps = [
            "trellis",
            "retopology",
            "pbr",
            "draco",
            "dwt_watermark",
            "checkpoints",
            "nobg",
            "sam",
            "usdz",
            "video_360",
        ]
        if os.getenv("TRELLIS_VERSION", "2").strip().lower() in ("2", "trellis2", "trellis.2"):
            caps.append("trellis2")
        if PIPELINE_MODE == "stub":
            caps.append("stub")
        return caps

    def _ws_connect_cm(self, url: str, headers: dict):
        connect_kwargs = {
            "ping_interval": 20,
            "ping_timeout": 20,
            "open_timeout": WS_CONNECT_TIMEOUT,
        }
        try:
            return websockets.connect(url, additional_headers=headers, **connect_kwargs)
        except TypeError:
            try:
                return websockets.connect(url, extra_headers=headers, **connect_kwargs)
            except TypeError:
                return websockets.connect(url, **connect_kwargs)

    async def connect(self) -> None:
        headers = {"Authorization": f"Bearer {WORKER_TOKEN}"}
        backoff = 1
        urls = [ORCHESTRATOR_URL]
        if WS_FALLBACK_URL and WS_FALLBACK_URL not in urls:
            urls.append(WS_FALLBACK_URL)
        while True:
            for url in urls:
                try:
                    logger.info("Connecting to %s as %s (Tailscale/primary or WSS fallback)", url, self.worker_id)
                    async with self._ws_connect_cm(url, headers) as ws:
                        self._ws = ws
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "ready",
                                    "worker_id": self.worker_id,
                                    "version": "0.4.0",
                                    "capabilities": self._capabilities(),
                                    "weight": float(os.getenv("WORKER_WEIGHT", "0")),
                                    "pipeline_mode": PIPELINE_MODE,
                                }
                            )
                        )
                        backoff = 1
                        hb = asyncio.create_task(self.send_heartbeat(ws))
                        mx = asyncio.create_task(self.send_metrics(ws))
                        try:
                            async for message in ws:
                                await self.handle_message(message, ws)
                        finally:
                            self._ws = None
                            hb.cancel()
                            mx.cancel()
                            if self._task_coro and not self._task_coro.done():
                                logger.info(
                                    "WS closed, waiting for background task (до %ss)…",
                                    TASK_DRAIN_TIMEOUT_SEC,
                                )
                                try:
                                    await asyncio.wait_for(self._task_coro, timeout=TASK_DRAIN_TIMEOUT_SEC)
                                except asyncio.TimeoutError:
                                    logger.warning("Background task did not finish after WS close")
                except Exception as exc:  # noqa: BLE001
                    logger.warning("WS %s failed: %s", url, exc)
                    continue
            logger.warning("All WS endpoints failed; retry in %ss", backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)


if __name__ == "__main__":
    agent = WorkerAgent()
    asyncio.run(agent.connect())
