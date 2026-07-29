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
