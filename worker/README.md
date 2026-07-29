# Образ воркера

## Локально (ПК) — stub, без TRELLIS

```bash
docker build -t kwork-worker:stub worker
docker run --env-file .env -e WORKER_PIPELINE_MODE=stub kwork-worker:stub
```

Или из корня репо:

```bash
docker compose --profile worker up -d worker-stub
```

## TRELLIS.2 — только Intelion Cloud GPU

### Локальный GPU: один раз «запечь» runtime в образ

После первого старта `install_trellis_runtime.sh` (flexgemm, o_voxel) — сохранить контейнер:

```bash
# воркер уже running, runtime дособрался
./scripts/worker_docker_bake.sh
# → kwork-worker:trellis2-runtime

# опционально: файл для переноса
./scripts/worker_docker_bake.sh kwork-worker kwork-worker:trellis2-runtime ./kwork-worker-runtime.tar
```

В `.env` / web-admin укажите образ `kwork-worker:trellis2-runtime` — recreate больше не тянет зависимости.

### Облако Intelion

Сборка **не на Windows/WSL**. На VM Intelion через `provision.py`:

```bash
python worker/cloud/provision.py --action create --gpu rtx4090
# → bootstrap-{id}.sh на SSH
```

См. [cloud/README.md](cloud/README.md).

Ручная сборка на Linux-GPU (если нужно):

```bash
docker build --build-arg INSTALL_TRELLIS=1 --build-arg DOWNLOAD_WEIGHTS=1 \
  --build-arg TRELLIS_VERSION=2 --build-arg INSTALL_FLASH_ATTN=0 \
  -t kwork-worker:trellis2 worker
```

- Repo: [microsoft/TRELLIS.2](https://github.com/microsoft/TRELLIS.2)
- Weights: [microsoft/TRELLIS.2-4B](https://huggingface.co/microsoft/TRELLIS.2-4B)
- **VRAM:** ≥24 GB (A100/H100). RTX 4090/A6000 — `512` + `TRELLIS2_LOW_VRAM=1`

`TRELLIS_ALLOW_STUB_FALLBACK=1` — только отладка.

## Без фона

`WORKER_TRELLIS_INPROCESS=0` (по умолчанию) — TRELLIS в **отдельном subprocess**, VRAM освобождается после шага. `TRELLIS_SKIP_INTERNAL_REMBG=1` — не держим BiRefNet внутри TRELLIS (фон уже снят `remove_background.py`).

## Кэш (не скачивать и не компилировать повторно)

| Что | Где |
|-----|-----|
| Веса HF (TRELLIS, RMBG) | volume/host: `~/hf_cache` → `/root/.cache/huggingface` |
| flexgemm, o_voxel | маркер `kwork_worker_state:/var/lib/worker/trellis_runtime_done` или bake-образ |
| torch / triton / CUDA JIT | `kwork_worker_state` (`setup_worker_cache.sh`) |
| DINOv3 (gated) | локально: `/var/lib/worker/dinov3-vitl16` или `TRELLIS2_DINOV3_LOCAL` |
| Прогрев GPU при старте | `WORKER_STARTUP_WARMUP=1` (по умолчанию), маркер `gpu_warmup_sig` |

Первый старт долгий; второй — веса из кэша, runtime skip, warmup skip. После первого успешного старта: `./scripts/worker_docker_bake.sh` — extensions в образ.

Принудительно: `WORKER_PREFETCH_FORCE=1`, `WORKER_GPU_WARMUP_FORCE=1`.

### DINOv3 gated (403 / rejected)

Модель: `facebook/dinov3-vitl16-pretrain-lvd1689m` (не dinov2).

1. На HF под **delfinchik** — Accept/Request access.
2. Или положить веса локально (с ПК где есть доступ):

```bash
# ПК с доступом к HF (новый CLI: hf, не huggingface-cli)
hf download facebook/dinov3-vitl16-pretrain-lvd1689m \
  --local-dir dinov3-vitl16 --token hf_...
```

tar czf dinov3.tgz dinov3-vitl16
scp dinov3.tgz dom@123:~/
```

```bash
# GPU-ПК
mkdir -p ~/dinov3-vitl16
tar xzf dinov3.tgz -C ~/
docker cp ~/dinov3-vitl16/. kwork-worker:/var/lib/worker/dinov3-vitl16/
docker restart kwork-worker
```

Или mount: `-v ~/dinov3-vitl16:/var/lib/worker/dinov3-vitl16:ro`

В логах: `[dinov3-local] готово`.
