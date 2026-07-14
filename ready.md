# ready.md — что уже сделано по ТЗ (реально, для прода)

Дата среза: 2026-07-12 (ночь).  
Источник: код + `Техническое задание 3DVektor.txt`.

---

## Worker / TRELLIS.2 / пайплайн (§5–§6, §17)

- **TRELLIS.2-4B** (`microsoft/TRELLIS.2-4B`): image→3D + native PBR, `trellis_runtime.py`
- Dockerfile default: `TRELLIS_VERSION=2`, `TRELLIS2_PIPELINE_TYPE=512`, `TRELLIS2_LOW_VRAM=1`
- RTX 5070: `ATTN_BACKEND=xformers`, resolution **512** (не 1024+)
- retopo/bake: copy при TRELLIS.2 (PBR уже в GLB); compress_draco — реальный
- Stub — только dev smoke, не production
- **Приёмка:** `e2e_trellis_acceptance.py --preflight --fail-on-budget`, runbook [`docs/deployment/GPU_E2E_RTX5070.md`](docs/deployment/GPU_E2E_RTX5070.md)
- TRELLIS.2 **single-image** (`view_00`), legacy multi-view — deprecated (`TRELLIS_VERSION=1`)
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
- Воронка публикации §7.9: admin dashboard + team funnel + CSV

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

### Compliance / security (2026-07-14)

- E2E шифрование фото §10.6.2: policy `e2e_photo_encryption`, mobile AES-GCM, worker decrypt in temp
- Vault/AES ПД §2.7, WB/Ozon upload scaffold §14.6

### Seller 2FA / NSFW SLA / shoot deep link / campaign A/B (2026-07-14)

- Seller `/settings`: профиль, пароль, TOTP 2FA, notification prefs; AuthCard 2FA challenge
- NSFW SLA escalate: Celery + `POST /admin/nsfw/escalate` + ModerationPage
- Mobile `/shoot/{token}` guest AR flow + Android deep link + web «Открыть в приложении»
- Campaigns A/B: `ab_enabled`, stats funnel/by_variant/CTR, `GET /campaigns/{id}/click`
- Миграция `023_prefs_campaign_clicks`

### Access log / audit / alerts / NSFW preview (2026-07-14)

- Presigned put/get → `access_log` (models, photos/prepare, storage)
- Audit: `api_key_created|revoked`, `tariff_price_changed`
- Disk/SMART + GPU thermal dual-channel Telegram+email (`GPU_TEMP_ALERT_C=85`)
- NSFW photo previews + `moderation_blacklist` CRUD; миграция `024`

### Shoot stats / UL / click / restore / cancel (2026-07-14)

- Shoot-link stats §3.15.4 admin+company UI
- iOS Universal Links + AASA/assetlinks + kworkmob scheme
- Campaign CTA click tracker в email/push
- Restore sources API + audit/access_log; cancel → `order_cancelled`
