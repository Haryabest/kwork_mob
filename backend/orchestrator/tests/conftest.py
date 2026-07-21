"""Общие фикстуры pytest: тестовая БД (Postgres) и Redis (§1.4 / Phase P)."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _disable_gateway_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """CI: не копить rl:* в Redis на всём прогоне pytest."""
    monkeypatch.setenv("RATE_LIMIT_DISABLED", "1")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: тест требует живых Postgres/Redis (пропускается при недоступности)",
    )


def _prepare_schema_sync() -> bool:
    """Схема через sync psycopg2 — не трогаем async engine до pytest event loop."""
    import app.main  # noqa: F401
    from sqlalchemy import create_engine, text

    from app.core.config import settings
    from app.core.database import Base

    sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2", 1)
    try:
        engine = create_engine(sync_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        Base.metadata.create_all(engine)
        engine.dispose()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def _schema() -> None:
    if not _prepare_schema_sync():
        pytest.skip("Postgres недоступен — интеграционные тесты пропущены")
    yield


@pytest_asyncio.fixture(scope="session")
async def _test_engine(_schema):
    """NullPool + один event loop на сессию — asyncpg не переиспользует чужие loop."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    import app.core.database as db_mod
    from app.core.config import settings

    prev_engine = db_mod.engine
    prev_factory = db_mod.async_session
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    db_mod.engine = engine
    db_mod.async_session = factory
    try:
        yield engine
    finally:
        await engine.dispose()
        db_mod.engine = prev_engine
        db_mod.async_session = prev_factory


@pytest_asyncio.fixture
async def db(_test_engine):
    """Сессия SQLAlchemy на тестовой БД."""
    import app.core.database as db_mod

    async with db_mod.async_session() as session:
        yield session


@pytest_asyncio.fixture
async def client(_test_engine):
    """HTTP-клиент поверх ASGI-приложения с готовой схемой БД."""
    import app.core.redis as redis_mod

    redis_mod.redis_client = None
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    redis_mod.redis_client = None


@pytest_asyncio.fixture
async def redis_client(_test_engine):
    """Живой Redis c очисткой БД до и после теста; skip при недоступности."""
    import app.core.redis as redis_mod

    redis_mod.redis_client = None
    try:
        redis = await redis_mod.get_redis()
        await redis.ping()
    except Exception:
        redis_mod.redis_client = None
        pytest.skip("Redis недоступен")
        return
    await redis.flushdb()
    try:
        yield redis
    finally:
        await redis.flushdb()
        try:
            await redis.aclose()
        except Exception:
            pass
        redis_mod.redis_client = None


@pytest.fixture
def unique_email():
    """Фабрика уникальных email для регистрации в интеграционных тестах."""
    return lambda: f"test_{uuid.uuid4().hex[:8]}@example.com"
