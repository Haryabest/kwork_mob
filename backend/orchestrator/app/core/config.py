"""Конфигурация приложения."""

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ORCHESTRATOR_ROOT = Path(__file__).resolve().parents[2]
_ENV_CANDIDATES = [
    _ORCHESTRATOR_ROOT.parent.parent / ".env",
    _ORCHESTRATOR_ROOT / ".env",
    Path(".env"),
]
_ENV_FILES = tuple(str(p) for p in _ENV_CANDIDATES if p.exists()) or (".env",)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        extra="ignore",
        populate_by_name=True,
    )

    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me"
    API_BASE_URL: str = "http://localhost:8000"

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "kwork"
    POSTGRES_PASSWORD: str = "kwork_secret"
    POSTGRES_DB: str = "kwork_mob"

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SENTINELS: str = ""  # host:26379,host2:26379
    REDIS_SENTINEL_MASTER: str = "mymaster"
    REDIS_SENTINEL_PASSWORD: str = ""
    REDIS_PASSWORD: str = ""

    MINIO_ENDPOINT: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_PHOTOS: str = "photos"
    MINIO_BUCKET_MODELS: str = "models"
    MINIO_BUCKET_BACKUPS: str = "backups"
    MINIO_DISK_TOTAL_BYTES: int = 0  # для % заполнения в /storage/smart
    MINIO_SMART_JSON: str = ""  # путь к JSON от infra/agents/minio_smart_exporter
    MINIO_HA_JSON: str = ""  # HA: replication / PG lag / nodes (§11.16.2); fallback SMART JSON
    # §11.16.4 ops hooks (HTTP agent or local script)
    MINIO_FORCE_RESYNC_URL: str = ""
    MINIO_FORCE_RESYNC_SCRIPT: str = ""
    PATRONI_RESTART_REPL_URL: str = ""
    PATRONI_RESTART_REPL_SCRIPT: str = ""
    # §11.16.4 FIO disk test (10 sec)
    FIO_TEST_URL: str = ""
    FIO_TEST_SCRIPT: str = ""
    # §11.16.4 Docker/Loki logs
    LOKI_URL: str = ""  # http://loki:3100
    DOCKER_LOGS_PROXY_URL: str = ""  # agent POST /logs
    DOCKER_LOG_CONTAINERS: str = "postgres,minio,patroni,redis,clickhouse,orchestrator,haproxy"

    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    CLICKHOUSE_DB: str = "kwork_metrics"

    JWT_SECRET: str = "change-me-jwt"
    JWT_ACCESS_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_EXPIRE_DAYS: int = 30

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@kworkmob.local"

    EMAIL_VERIFY_CODE_TTL_SECONDS: int = 900
    PASSWORD_RESET_TTL_SECONDS: int = 3600

    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""
    # Webhook authenticity §8.4.1 (IP allowlist + GET payment)
    YOOKASSA_WEBHOOK_IP_CHECK: bool = True
    YOOKASSA_WEBHOOK_ALLOW_PRIVATE: bool = False  # localhost/dev behind Tailscale
    YOOKASSA_WEBHOOK_IP_ALLOWLIST: str = ""  # empty → official YooKassa CIDRs
    SELLER_PUBLIC_URL: str = "http://localhost:3000"
    MOBILE_OAUTH_REDIRECT_URI: str = "kworkmob://open/oauth/callback"

    # OAuth VK / Yandex / Sber ID (§2.2.3 — расширение email+пароль)
    OAUTH_VK_CLIENT_ID: str = ""
    OAUTH_VK_CLIENT_SECRET: str = ""
    OAUTH_YANDEX_CLIENT_ID: str = ""
    OAUTH_YANDEX_CLIENT_SECRET: str = ""
    OAUTH_SBER_CLIENT_ID: str = ""
    OAUTH_SBER_CLIENT_SECRET: str = ""
    OAUTH_STATE_TTL_SECONDS: int = 600

    WORKER_TOKEN: str = "worker-dev-token"

    # Облако Intelion / Immers (§11.3.3 / §14.7)
    CLOUD_PROVIDER: str = "intelion"
    CLOUD_API_TOKEN: str = ""
    CLOUD_INTELION_TOKEN: str = ""
    CLOUD_IMMERS_TOKEN: str = ""
    CLOUD_API_BASE: str = ""
    CLOUD_INTELION_API_BASE: str = ""
    CLOUD_IMMERS_API_BASE: str = ""
    CLOUD_API_MOCK: bool = False
    INTELION_FLAVOR_ID: int = 0
    INTELION_OS_ID: int = 0
    INTELION_SSD_GB: int = 100
    # §11.3.3 / soft-launch: лимит расходов на облачные GPU (0 = без лимита)
    CLOUD_MONTHLY_BUDGET_RUB: int = 0
    CLOUD_DAILY_BUDGET_RUB: int = 0
    CLOUD_BURN_ALERT_RUB_PER_HOUR: int = 500
    CLOUD_BUDGET_ALERT_COOLDOWN_SEC: int = 3600

    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    GRACE_PERIOD_SECONDS: int = 25
    HEARTBEAT_INTERVAL_SECONDS: int = 5
    HEARTBEAT_TIMEOUT_SECONDS: int = 20

    # Эскалации §4.2 / §13
    ESCALATION_QUEUE_MINUTES: int = 30
    ESCALATION_PROCESSING_MINUTES: int = 20
    ESCALATION_MAX: int = 3

    WATERMARK_HMAC_SECRET: str = "change-me-watermark"

    # NSFW §10.8: off | heuristic | nudenet | auto
    NSFW_MODE: str = "auto"
    NSFW_THRESHOLD: float = 0.85
    NSFW_FORCE_BLOCK: bool = False

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # GPU thermal alert §12.4.1 / §13.4
    GPU_TEMP_ALERT_C: int = 85
    GPU_TEMP_ALERT_COOLDOWN_SEC: int = 600

    # Ops alerts §12.4.1
    QUEUE_ALERT_LENGTH: int = 20
    QUEUE_ALERT_COOLDOWN_SEC: int = 900
    ALL_BUSY_ALERT_MINUTES: int = 5
    ALL_BUSY_ALERT_COOLDOWN_SEC: int = 900
    WORKER_OFFLINE_ALERT_SECONDS: int = 30
    WORKER_OFFLINE_ALERT_COOLDOWN_SEC: int = 600

    # Shoot-link photo TTL §3.15.4
    SHOOT_LINK_PHOTO_TTL_DAYS: int = 7
    # §9.1.2 облачная копия исходников
    SOURCE_PHOTOS_TTL_DAYS: int = 30
    # §23.7 maintenance
    SERVICE_LOG_RETENTION_DAYS: int = 14
    BACKUP_RESTORE_TEST_URL: str = ""
    BACKUP_RESTORE_TEST_SCRIPT: str = ""

    # Quality alerts §12.4.1
    PUBLICATION_CONVERSION_ALERT_RATIO: float = 0.30
    FALLBACK_SEGMENTATION_ALERT_RATIO: float = 0.15
    FALLBACK_SEGMENTATION_MIN_SAMPLES: int = 10

    # Corporate / payment alerts §12.4.1
    YOOKASSA_ERROR_STREAK_ALERT: int = 5
    YOOKASSA_WEBHOOK_FAIL_STREAK: int = 5
    COMPANY_WEBHOOK_FAIL_STREAK: int = 3  # ERP §14.5.4
    COMPANY_LOW_BALANCE_ALERT_RUB: int = 5000
    COMPANY_SUSPICIOUS_ORDERS_10M: int = 50
    COMPANY_SUSPICIOUS_WINDOW_MIN: int = 10
    SHOOT_LINK_MASS_LIMIT_PER_HOUR: int = 100
    SHOOT_LINK_MASS_BLOCK_HOURS: int = 1
    API_KEY_DEFAULT_RATE_LIMIT: int = 1000
    API_KEY_DEFAULT_DAILY_LIMIT: int = 100_000

    # Universal Links / App Links (§3.15)
    APPLE_TEAM_ID: str = ""
    IOS_BUNDLE_ID: str = "com.kwork.mob.kworkMobile"
    ANDROID_PACKAGE_NAME: str = "com.kwork.mob.kwork_mobile"
    ANDROID_SHA256_FINGERPRINTS: str = ""  # comma-separated

    # FCM (§3.4.3 / §11.8)
    FCM_SERVER_KEY: str = ""
    FCM_SERVICE_ACCOUNT_JSON: str = ""  # path to service account JSON
    FCM_PROJECT_ID: str = ""

    # Staff panel (§11): VPN WireGuard/Tailscale + TOTP 2FA
    ADMIN_VPN_REQUIRED: bool = False
    # CIDR через запятую: Tailscale CGNAT + типичные WG
    ADMIN_VPN_CIDRS: str = "100.64.0.0/10,10.0.0.0/8,172.16.0.0/12"
    ADMIN_2FA_REQUIRED: bool = Field(
        default=True,
        validation_alias=AliasChoices("ADMIN_2FA_REQUIRED", "ADMIN_2FA_ENABLED"),
    )
    STAFF_JWT_ACCESS_EXPIRE_MINUTES: int = 480  # 8 часов по ТЗ
    STAFF_IDLE_TIMEOUT_MINUTES: int = 30

    # §2.7 ПД at rest (AES-256-GCM)
    PD_ENCRYPTION_KEY: str = ""  # base64url, 32 bytes
    VAULT_ADDR: str = ""
    VAULT_TOKEN: str = ""
    VAULT_PD_KEY_PATH: str = "secret/data/kwork/pd_encryption_key"

    # §7.6 / §14.6 WB/Ozon API upload (scaffold)
    MARKETPLACE_UPLOAD_ENABLED: bool = False
    WB_API_BASE_URL: str = "https://content-api.wildberries.ru"
    WB_3D_UPLOAD_PATH: str = "/content/v3/media/file"
    OZON_API_BASE_URL: str = "https://api-seller.ozon.ru"
    OZON_3D_UPLOAD_PATH: str = "/v1/product/3d-model/upload"
    MARKETPLACE_UPLOAD_MAX_RETRIES: int = 3

    # §10.6.3 MinIO SSE: none | sse-s3 | sse-kms
    MINIO_SSE_MODE: str = "sse-s3"
    MINIO_KMS_KEY_ID: str = ""  # Key ID для SSE-KMS (MinIO / Vault Transit)
    VAULT_MINIO_KMS_KEY_PATH: str = "secret/data/kwork/minio_kms_key_id"

    # §10.6.2 E2E шифрование фото (company policy e2e_photo_encryption)
    PHOTO_E2E_ENCRYPTION_MASTER: bool = True

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "https://www.wildberries.ru",
        "https://wildberries.ru",
        "https://www.ozon.ru",
        "https://ozon.ru",
        "https://seller.wildberries.ru",
        "https://seller.ozon.ru",
    ]

    # §10.3 Referer check на выдачу download
    DOWNLOAD_REFERER_CHECK: bool = True
    DOWNLOAD_ALLOW_EMPTY_REFERER: bool = True  # native mobile без Referer
    DOWNLOAD_REFERER_HOSTS: str = ""  # доп. хосты через запятую

    @property
    def download_referer_hosts(self) -> list[str]:
        return [c.strip() for c in self.DOWNLOAD_REFERER_HOSTS.split(",") if c.strip()]

    @property
    def vpn_cidrs(self) -> list[str]:
        return [c.strip() for c in self.ADMIN_VPN_CIDRS.split(",") if c.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


settings = Settings()
