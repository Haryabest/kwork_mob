# Облачные GPU-воркеры: Intelion + Immers

| Провайдер | Сайт | API | Поддержка |
|-----------|------|-----|-----------|
| **Intelion** | [intelion.cloud](https://intelion.cloud/) | [api](https://intelion.cloud/api/) v2 | Telegram `@CareIntelionCloud_bot` |
| **Immers** | [immers.cloud](https://immers.cloud/) | [api](https://immers.cloud/api/) | Личный кабинет / support |

TRELLIS собирается на GPU-VM через `bootstrap-{id}.sh`, не на домашнем ПК.

## Env (.env)

```bash
# Intelion
CLOUD_INTELION_TOKEN=...
INTELION_FLAVOR_ID=1
INTELION_OS_ID=1

# Immers
CLOUD_IMMERS_TOKEN=...
IMMERS_FLAVOR_ID=1
IMMERS_OS_ID=1

# или один токен на оба (fallback)
CLOUD_API_TOKEN=...

CLOUD_API_MOCK=0   # 1 — локальный mock без API
```

## CLI

```bash
python worker/cloud/provision.py --action providers

python worker/cloud/provision.py --action flavors --provider intelion
python worker/cloud/provision.py --action create --provider intelion --gpu rtx4090 --flavor-id 1 --os-id 1

python worker/cloud/provision.py --action flavors --provider immers
python worker/cloud/provision.py --action create --provider immers --gpu rtx4090 --flavor-id 1 --os-id 1
```

## Admin API

- `GET /api/v1/admin/cloud/providers`
- `GET /api/v1/admin/cloud/flavors?provider=intelion|immers`
- `POST /api/v1/admin/cloud/instances` — поле `provider`, `flavor_id`, `os_id`

## Immers OpenStack

Immers также даёт native [OpenStack Zed API](https://immers.cloud/api/) для продвинутой автоматизации.
Cabinet API v2 (как Intelion) покрывает create/flavors/os-images; если endpoints отличаются —
переопредели `IMMERS_PATH_*` в `.env`.
