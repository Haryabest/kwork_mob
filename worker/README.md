# Образ воркера

## Stub (dev / CI без GPU)
```bash
docker build -t kwork-worker:stub .
docker run --env-file ../../.env.worker -e WORKER_PIPELINE_MODE=stub kwork-worker:stub
```

## TRELLIS.2 (production GPU — требование клиента)
```bash
docker build --build-arg INSTALL_TRELLIS=1 --build-arg TRELLIS_VERSION=2 -t kwork-worker:trellis2 .

docker run --gpus all \
  -e WORKER_PIPELINE_MODE=trellis \
  -e TRELLIS_VERSION=2 \
  -e TRELLIS_WEIGHTS=microsoft/TRELLIS.2-4B \
  -e TRELLIS2_PIPELINE_TYPE=512 \
  -e TRELLIS2_LOW_VRAM=1 \
  ...
  kwork-worker:trellis2
```

- Repo: [microsoft/TRELLIS.2](https://github.com/microsoft/TRELLIS.2)
- Weights: [microsoft/TRELLIS.2-4B](https://huggingface.co/microsoft/TRELLIS.2-4B)
- **VRAM:** официально ≥24 GB (A100/H100). RTX 5070 — пробовать `512` + `TRELLIS2_LOW_VRAM=1`, иначе облако.
- TRELLIS.2: **single-image** + native PBR; 12 ракурсов → берём `view_00` (фронт), nobg уже с нашего пайплайна.

## TRELLIS v1 (legacy, multi-view)
```bash
docker build --build-arg TRELLIS_REPO=https://github.com/microsoft/TRELLIS.git \
  --build-arg TRELLIS_VERSION=1 -t kwork-worker:trellis1 .
```

`TRELLIS_ALLOW_STUB_FALLBACK=1` — только отладка (при ошибке TRELLIS пишет stub GLB).

## Без фона
`WORKER_REAL_NOBG=1` (по умолчанию в агенте) → rembg / DeepLab / GrabCut.
