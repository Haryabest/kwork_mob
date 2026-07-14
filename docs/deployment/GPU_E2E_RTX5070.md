# GPU E2E приёмка — RTX 5070 (дома)

Цель: один прогон `e2e_trellis_acceptance.py` на **RTX 5070 (sm_120, 12 GB VRAM)** с TRELLIS.2, бюджет **≤180 с** (`WORKER_DEPLOY=local`).

## Требования

| Компонент | Версия |
|-----------|--------|
| GPU | NVIDIA RTX 5070, driver ≥565 |
| CUDA | 12.8 (PyTorch **cu128**) |
| VRAM | 12 GB — `TRELLIS2_PIPELINE_TYPE=512`, `TRELLIS2_LOW_VRAM=1` |
| Docker | GPU runtime (`--gpus all`) |
| Фото | 12 ракурсов `view_00…view_11.jpg` или одно фото (E2E дублирует) |

## Быстрый старт (PowerShell)

```powershell
cd C:\kwork_mob
.\worker\scripts\run_e2e_home.ps1 -PhotosDir D:\samples\dome12
```

Скрипт выставляет:

- `WORKER_DEPLOY=local` → бюджет 180 с  
- `TRELLIS_VERSION=2`, `TRELLIS2_PIPELINE_TYPE=512`, `TRELLIS2_LOW_VRAM=1`  
- `TRELLIS_ALLOW_STUB_FALLBACK=0`  
- `--preflight --fail-on-budget`

## Docker (рекомендуется)

```powershell
docker build --build-arg INSTALL_TRELLIS=1 --build-arg DOWNLOAD_WEIGHTS=1 `
  --build-arg TRELLIS_VERSION=2 -t kwork-worker:trellis2 worker

docker run --rm --gpus all `
  -v D:\samples\dome12:/photos:ro `
  -e WORKER_DEPLOY=local `
  -e WORKER_PIPELINE_MODE=trellis `
  -e TRELLIS_VERSION=2 `
  -e TRELLIS_WEIGHTS=microsoft/TRELLIS.2-4B `
  -e TRELLIS2_PIPELINE_TYPE=512 `
  -e TRELLIS2_LOW_VRAM=1 `
  -e ATTN_BACKEND=xformers `
  -e TRELLIS_ALLOW_STUB_FALLBACK=0 `
  kwork-worker:trellis2 `
  python3 /app/scripts/e2e_trellis_acceptance.py --photos /photos --preflight --fail-on-budget
```

## Exit codes

| Code | Значение |
|------|----------|
| 0 | OK, в бюджете |
| 1 | Пайплайн упал |
| 2 | Превышен бюджет (`--fail-on-budget`) |
| 3 | Preflight: нет CUDA / cu128 / весов |

## Отчёт

JSON: `worker/e2e_reports/acceptance_*.json` — поля `step_timings`, `trellis_version`, `cuda`, `gpu_profile`.

## TRELLIS.2 vs legacy

- **Production:** один вход `photos_nobg/view_00` (single-image), native PBR в GLB.  
- **Legacy TRELLIS v1:** multi-view 12 кадров — только при `TRELLIS_VERSION=1`, не для RTX 5070 приёмки.

## Troubleshooting

| Симптом | Решение |
|---------|---------|
| `sm_120 requires PyTorch cu128` | Пересобрать образ с `install_trellis2.sh` |
| OOM 12 GB | `TRELLIS2_LOW_VRAM=1`, `512` pipeline |
| `photos_nobg/view_00` missing | Нормально: `remove_background` идёт первым в E2E |
| Stub GLB | `TRELLIS_ALLOW_STUB_FALLBACK=0` обязателен для приёмки |

См. также: [`ЗАВТРА_ЛОКАЛЬНЫЙ_ЗАПУСК.md`](../ЗАВТРА_ЛОКАЛЬНЫЙ_ЗАПУСК.md)
