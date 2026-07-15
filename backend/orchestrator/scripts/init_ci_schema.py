"""Create ORM schema for CI smoke (mobile-backend-smoke job)."""

from __future__ import annotations

import asyncio

import app.main  # noqa: F401 — register models
from app.core.database import Base, engine


async def _run() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_run())
