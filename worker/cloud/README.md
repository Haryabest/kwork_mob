# Облачные GPU-воркеры

Провайдеры из `Адреса Облачных Воркеров.txt`:

| Провайдер | Сайт | API |
|-----------|------|-----|
| IntelionCloud | https://intelion.cloud/ | https://intelion.cloud/api/ |
| Immers | https://immers.cloud/ | https://immers.cloud/api/ |

Telegram: `@CareIntelionCloud_bot`

## Роль в архитектуре

Воркеры (раздел 3 `Архитектура 3dvektor.txt`) — домашние ПК или облачные GPU-инстансы.
Каждый узел:
1. Входит в Tailscale (основной канал) или резервный WSS к оркестратору
2. Поднимает Docker-образ `worker/` (TRELLIS + agent)
3. Шлёт heartbeat `/ws/worker` каждые 5 сек
4. Скачивает ZIP из MinIO → генерация → upload результата → очистка temp

## Быстрый старт (скрипт)

```bash
# из корня репо
export ORCHESTRATOR_WS_URL=wss://api.example.com/ws/worker
export WORKER_TOKEN=...
export CLOUD_PROVIDER=intelion   # или immers
export CLOUD_API_TOKEN=...

python worker/cloud/provision.py --action status
python worker/cloud/provision.py --action start --gpu a10
python worker/cloud/provision.py --action stop
```

Пока API провайдеров не зафиксированы в SDK — скрипт печатает чеклист и пишет `.env.worker` для ручного деплоя.
