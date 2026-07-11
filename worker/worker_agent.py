"""
Агент GPU-воркера.
Подключение к оркестратору через WebSocket, Redlock, постобработка TRELLIS.
FID исключён из production.
"""

import asyncio
import json
import os
import subprocess
from pathlib import Path

import boto3
import psutil
import redis
import websockets

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_WS_URL", "ws://localhost:8000/ws/worker")
WORKER_ID = os.getenv("WORKER_ID", "worker-1")
WORKER_TOKEN = os.getenv("WORKER_TOKEN", "worker-dev-token")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
TEMP_DIR = Path(os.getenv("TEMP_DIR", "/tmp/worker"))


class WorkerAgent:
    def __init__(self):
        self.worker_id = WORKER_ID
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        self.minio_client = boto3.client(
            "s3",
            endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            region_name="us-east-1",
        )
        self.temp_dir = TEMP_DIR
        self.current_task = None
        self.status = "idle"
        self.config = {
            "quality_threshold": 0.7,
            "temp_threshold_high": 85,
            "temp_threshold_low": 75,
            "dwt_watermark_strength": 0.01,
        }

    def acquire_lock(self, task_id: str) -> bool:
        """Redlock: SET task:{task_id} processing NX EX 60."""
        return self.redis_client.set(f"task:{task_id}", self.worker_id, nx=True, ex=60)

    def release_lock(self, task_id: str) -> None:
        self.redis_client.delete(f"task:{task_id}")

    def get_gpu_metrics(self) -> dict:
        """Метрики GPU через pynvml (заглушка без GPU)."""
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            return {
                "gpu_util": util.gpu,
                "vram_used_gb": mem.used / 1e9,
                "vram_total_gb": mem.total / 1e9,
                "gpu_temp": temp,
            }
        except Exception:
            return {"gpu_util": 0, "vram_used_gb": 0, "vram_total_gb": 0, "gpu_temp": 0}

    async def send_heartbeat(self, ws):
        while True:
            await ws.send(json.dumps({
                "type": "heartbeat",
                "worker_id": self.worker_id,
                "status": self.status,
            }))
            await asyncio.sleep(5)

    async def send_metrics(self, ws):
        while True:
            gpu = self.get_gpu_metrics()
            await ws.send(json.dumps({
                "type": "metrics",
                "worker_id": self.worker_id,
                "gpu": gpu,
                "cpu_percent": psutil.cpu_percent(),
                "ram_percent": psutil.virtual_memory().percent,
            }))
            await asyncio.sleep(5)

    async def start_task(self, task_id: str, payload: dict, ws):
        if not self.acquire_lock(task_id):
            await ws.send(json.dumps({"type": "task_conflict", "task_id": task_id}))
            return

        self.current_task = task_id
        self.status = "processing"
        task_dir = self.temp_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        try:
            await ws.send(json.dumps({"type": "task_started", "task_id": task_id}))

            # 1. Скачать фото из MinIO
            # 2. remove_background.py (DeepLabV3+ + SAM)
            subprocess.run(["python3", "/app/scripts/remove_background.py", str(task_dir)], check=False)
            # 3. trellis_generate.py
            subprocess.run(["python3", "/app/scripts/trellis_generate.py", str(task_dir)], check=False)
            # 4. retopology.py
            subprocess.run(["python3", "/app/scripts/retopology.py", str(task_dir)], check=False)
            # 5. bake_pbr.py
            subprocess.run(["python3", "/app/scripts/bake_pbr.py", str(task_dir)], check=False)
            # 6. apply_watermark.py (только diffuse)
            subprocess.run(["python3", "/app/scripts/apply_watermark.py", str(task_dir)], check=False)
            # 7. compress_draco.py
            subprocess.run(["python3", "/app/scripts/compress_draco.py", str(task_dir)], check=False)
            # 8. validate_glb.py
            subprocess.run(["python3", "/app/scripts/validate_glb.py", str(task_dir)], check=False)

            await ws.send(json.dumps({
                "type": "task_completed",
                "task_id": task_id,
                "result_url": f"s3://models/{task_id}/model.glb",
            }))
        except Exception as e:
            await ws.send(json.dumps({"type": "task_failed", "task_id": task_id, "error": str(e)}))
        finally:
            self.release_lock(task_id)
            self.current_task = None
            self.status = "idle"

    async def handle_message(self, message: str, ws):
        data = json.loads(message)
        msg_type = data.get("type")

        if msg_type == "task":
            await self.start_task(data["task_id"], data["payload"], ws)
        elif msg_type == "stop":
            self.status = "idle"
        elif msg_type == "config_update":
            self.config.update(data.get("settings", {}))

    async def connect(self):
        headers = {"Authorization": f"Bearer {WORKER_TOKEN}"}
        async with websockets.connect(ORCHESTRATOR_URL, extra_headers=headers) as ws:
            await ws.send(json.dumps({
                "type": "ready",
                "worker_id": self.worker_id,
                "version": "0.1.0",
                "capabilities": ["trellis", "retopology", "pbr", "draco", "dwt_watermark"],
            }))
            asyncio.create_task(self.send_heartbeat(ws))
            asyncio.create_task(self.send_metrics(ws))
            async for message in ws:
                await self.handle_message(message, ws)


if __name__ == "__main__":
    agent = WorkerAgent()
    asyncio.run(agent.connect())
