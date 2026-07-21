"""Точка входа FastAPI-приложения (оркестратор + API Gateway)."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import async_session
from app.core.middleware import ApiRequestLogMiddleware, RateLimitMiddleware, RobotsTagMiddleware
from app.services.dispatcher import start_dispatcher, stop_dispatcher
from app.services.queue import queue_service
from app.websocket.routes import ws_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from app.services.minio import minio_service

        minio_service.ensure_buckets()
    except Exception as exc:  # noqa: BLE001
        logger.warning("MinIO init skipped: %s", exc)

    try:
        async with async_session() as db:
            restored = await queue_service.sync_from_postgres(db)
            if restored:
                logger.info("Restored %s queue items from Postgres", restored)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Queue sync skipped: %s", exc)

    try:
        from app.core.crypto import ensure_pii_encryption_ready

        ensure_pii_encryption_ready()
    except Exception as exc:  # noqa: BLE001
        if not settings.is_development:
            raise
        logger.warning("PII encryption check skipped: %s", exc)

    start_dispatcher()
    yield
    await stop_dispatcher()


app = FastAPI(
    title="KWork Mob API",
    description="API платформы 3D-моделей для маркетплейсов",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ApiRequestLogMiddleware)
app.add_middleware(RobotsTagMiddleware)

app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)


@app.get("/.well-known/apple-app-site-association", include_in_schema=False)
async def public_apple_app_site_association():
    """Universal Links AASA (§3.15) — без VPN/auth."""
    from fastapi.responses import JSONResponse

    from app.services import applinks as al

    return JSONResponse(content=al.apple_app_site_association_public(), media_type="application/json")


@app.get("/.well-known/assetlinks.json", include_in_schema=False)
async def public_android_assetlinks():
    """Android App Links (§3.15)."""
    from app.services import applinks as al

    return al.android_assetlinks()


@app.get("/health")
async def health():
    from app.core.crypto import pii_encryption_status

    pii = pii_encryption_status()
    status = "ok" if pii.get("ok") else "degraded"
    return {"status": status, "service": "orchestrator", "pii_encryption": pii}


@app.get("/metrics")
async def metrics():
    """Prometheus scrape endpoint (§12)."""
    from fastapi.responses import Response

    from app.services.metrics import prometheus_metrics

    body, content_type = prometheus_metrics()
    return Response(content=body, media_type=content_type)
