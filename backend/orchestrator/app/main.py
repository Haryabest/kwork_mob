"""Точка входа FastAPI-приложения (оркестратор + API Gateway)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.middleware import RateLimitMiddleware, RobotsTagMiddleware
from app.websocket.routes import ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: инициализация Redis, PostgreSQL, синхронизация очереди
    yield
    # TODO: graceful shutdown


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
app.add_middleware(RobotsTagMiddleware)

app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "orchestrator"}
