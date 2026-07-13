# ready.md — что уже сделано по ТЗ (реально, для прода)

Дата среза: 2026-07-12 (ночь).  
Источник: код + `Техническое задание 3DVektor.txt`.

---

## Worker / TRELLIS / пайплайн (§5–§6, §17)

- Dockerfile: **default `WORKER_PIPELINE_MODE=trellis`**, `INSTALL_TRELLIS=1`, `DOWNLOAD_WEIGHTS=1`, SAM weights
- E2E budget логирование ≤180с local / ≤300с cloud
- **Приёмка:** `worker/scripts/e2e_trellis_acceptance.py` (wall-time + `--fail-on-budget`) — прогон на GPU с весами
- `remove_background`: rembg → DeepLab → **SAM** → GrabCut
- `retopology` / `bake_pbr` / `compress_draco` / `export_usdz_tryon` / `render_video_360` / `apply_hole_filling`
- Tailscale entrypoint + WS fallback
- Watermark DWT + validate GLB

---

## Облако Intelion/Immers (§11.3.3 / §14.7)

- REST client create/start/stop/flavors (+ `CLOUD_API_MOCK`)
- CLI `worker/cloud/provision.py`
- Оркестратор: `cloud_autoscaling` + admin API `/admin/cloud/*`
- Celery beat: autoscaling **каждые 30с**, costs/rules/instances
- Admin UI: WorkersPage — create/start/stop + правила + burn ₽/ч

---

## Маркетплейсы / viewer (§7)

- Добавление URL WB/Ozon (≤3), HTML-парсинг `model-viewer` / `.glb`
- Celery verify каждые **2ч**; force-verify в admin
- Бонус: промокод / free_generation (`publication_bonus_settings`)
- Share `/share/{hash}` + seller viewer с model-viewer
- Seller UI: ссылка на карточку, статусы, share

---

## HA / ops (§4, §9, §12, §22)

- `docker-compose.ha.yml`: MinIO ×2 + replication, Redis Sentinel ×3, PG primary+replica (Patroni scaffold)
- Docs: `docs/deployment/HA.md`
- Prometheus `/metrics`, ClickHouse, PG backup→MinIO, lifecycle
- Миграция **`012_cloud_pub`**

---

## B2B (§2.5, §4.8, §20)

- Members/roles/limits/sessions/audit, company balance, webhooks, API keys, `POST /models/import`

---

## Ранее готовое (ядро)

Auth, orders, NSFW, queue/dispatcher, YooKassa, promo/tariffs, campaigns/tax/upsells, seller/admin UI ядро, Flutter scaffold.

### P1 compliance (2026-07-13)

- СБП QR + фискальные чеки ЮKassa (НПД/УСН/ОСНО)
- Owner 2FA TOTP (`/auth/2fa/*`)
- Право на забвение + анонимизация финансов 5 лет
- SHA-256 ZIP + CORS/Referer на download
- Company balance topup через ЮKassa webhook
- Миграция `014_p1_compliance`

### P2 pipeline / mobile (2026-07-13)

- Instant Meshes (`/usr/local/bin/instant_meshes`) + target 100k–300k; Open3D fallback
- Blender в образе: PBR bake high→low, USDZ, video_360
- DWT: извлечение реальной diffuse + тесты JPEG/WebP 80% + `verify_watermark.py`
- Flutter: AR-слой (`ArSession` / MethodChannel) + FCM google-services scaffold

### P3 acceptance / AR / push / admin (2026-07-13)

- GPU E2E harness: `--preflight`, отчёт `e2e_reports/`, `run_e2e_home.ps1|sh`
- Native ARCore/ARKit plugins + gyro fallback
- FCM send (`app/services/push.py`) + `/admin/campaigns/push/test` + `scripts/push_e2e.py`
- Admin Dashboard на живых `/admin/metrics/dashboard` (ops/finance/b2b/quality/moderation)
- `model_feedback` + миграция `015_model_feedback`

### B2B / HA / ops (2026-07-13)

- Кастомные роли + permissions checklist + seller UI
- Webhooks DLQ/retry + Celery + Owner UI
- Campaigns auto: referral / nth_free / timed_discount
- Redis Sentinel client; Patroni image + compose profile
- Grafana JSON; ClickHouse MV в init; MinIO `/storage/smart`
- Миграция `016_b2b_ops`

См. пробелы: [`not-ready.md`](./not-ready.md).
