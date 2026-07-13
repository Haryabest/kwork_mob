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
    MINIO_DISK_TOTAL_BYTES: int = 0  # для % заполнения в /storage/smart

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
    SELLER_PUBLIC_URL: str = "http://localhost:3000"

    WORKER_TOKEN: str = "worker-dev-token"

    # Облако Intelion / Immers (§11.3.3 / §14.7)
    CLOUD_PROVIDER: str = "intelion"
    CLOUD_API_TOKEN: str = ""
    CLOUD_API_BASE: str = ""
    CLOUD_API_MOCK: bool = False

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
