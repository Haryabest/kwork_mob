"""Общие фикстуры pytest: тестовая БД (Postgres) и Redis (§1.4 / Phase P).

Фикстуры устроены так, чтобы:
- unit/slice-тесты работали без внешних сервисов;
- интеграционные тесты (`@pytest.mark.integration`) получали готовую схему БД
  и живой Redis, а при их недоступности — аккуратно пропускались (skip),
  что позволяет запускать набор и локально, и в CI (docker services).
"""

from __future__ import annotations

import asyncio
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
    """Создать схему в тестовой БД. Возвращает False, если Postgres недоступен."""
    import app.main  # noqa: F401 — регистрирует все ORM-модели в Base.metadata
    from sqlalchemy import text

    from app.core.database import Base, engine

    async def _run() -> bool:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception:
            return False
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # Освобождаем пул: соединения этого loop не должны утечь в тестовый loop.
        await engine.dispose()
        return True

    return asyncio.run(_run())


@pytest.fixture(scope="session")
def _schema() -> None:
    if not _prepare_schema_sync():
        pytest.skip("Postgres недоступен — интеграционные тесты пропущены")
    yield


@pytest_asyncio.fixture
async def db(_schema):
    """Сессия SQLAlchemy на тестовой БД."""
    from app.core.database import async_session

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def client(_schema):
    """HTTP-клиент поверх ASGI-приложения с готовой схемой БД."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def redis_client():
    """Живой Redis c очисткой БД до и после теста; skip при недоступности."""
    import app.core.redis as redis_mod

    # Пересоздаём singleton, чтобы клиент привязался к текущему event loop теста.
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
