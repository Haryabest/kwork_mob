# Образ воркера

## Stub (dev / CI без GPU)
```bash
docker build -t kwork-worker:stub .
docker run --env-file ../../.env.worker -e WORKER_PIPELINE_MODE=stub kwork-worker:stub
```

## TRELLIS (production GPU)
```bash
docker build --build-arg INSTALL_TRELLIS=1 --build-arg DOWNLOAD_WEIGHTS=1 -t kwork-worker:trellis .

# Локально / IntelionCloud:
docker run --gpus all \
  -e WORKER_PIPELINE_MODE=trellis \
  -e TRELLIS_ROOT=/app/trellis \
  -e TRELLIS_WEIGHTS=JeffreyXiang/TRELLIS-image-large \
  -e ORCHESTRATOR_WS_URL=wss://api.example.com/ws/worker \
  -e WORKER_TOKEN=... \
  -e MINIO_ENDPOINT=http://minio:9000 \
  -e REDIS_URL=redis://redis:6379/0 \
  --env-file ../../.env.worker \
  kwork-worker:trellis
```

Либо смонтировать клон [microsoft/TRELLIS](https://github.com/microsoft/TRELLIS):
```bash
-v /path/to/TRELLIS:/app/trellis -e TRELLIS_WEIGHTS=/path/to/weights
```

`TRELLIS_ALLOW_STUB_FALLBACK=1` — только отладка (при ошибке TRELLIS пишет stub GLB).

## Без фона
`WORKER_REAL_NOBG=1` (по умолчанию в агенте) → rembg / DeepLab / GrabCut.
