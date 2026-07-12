"""Реестр подключённых GPU-воркеров (in-memory + PG heartbeat)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket


@dataclass
class WorkerConnection:
    worker_id: str
    websocket: WebSocket
    status: str = "idle"
    weight: float = 0.0
    version: str = ""
    capabilities: list[str] = field(default_factory=list)
    current_task_id: str | None = None
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    meta: dict[str, Any] = field(default_factory=dict)


class WorkerHub:
    def __init__(self) -> None:
        self._workers: dict[str, WorkerConnection] = {}
        self._lock = asyncio.Lock()

    async def register(self, conn: WorkerConnection) -> None:
        async with self._lock:
            old = self._workers.get(conn.worker_id)
            if old and old.websocket is not conn.websocket:
                try:
                    await old.websocket.close(code=4000)
                except Exception:  # noqa: BLE001
                    pass
            self._workers[conn.worker_id] = conn

    async def unregister(self, worker_id: str, websocket: WebSocket | None = None) -> WorkerConnection | None:
        async with self._lock:
            conn = self._workers.get(worker_id)
            if not conn:
                return None
            if websocket is not None and conn.websocket is not websocket:
                return None
            return self._workers.pop(worker_id, None)

    async def get(self, worker_id: str) -> WorkerConnection | None:
        async with self._lock:
            return self._workers.get(worker_id)

    async def touch(self, worker_id: str, *, status: str | None = None, meta: dict | None = None) -> None:
        async with self._lock:
            conn = self._workers.get(worker_id)
            if not conn:
                return
            conn.last_heartbeat = datetime.now(timezone.utc)
            if status:
                conn.status = status
            if meta:
                conn.meta.update(meta)

    async def set_busy(self, worker_id: str, task_id: str) -> None:
        async with self._lock:
            conn = self._workers.get(worker_id)
            if conn:
                conn.status = "busy"
                conn.current_task_id = task_id

    async def set_idle(self, worker_id: str) -> None:
        async with self._lock:
            conn = self._workers.get(worker_id)
            if conn:
                if conn.status != "overheated":
                    conn.status = "idle"
                conn.current_task_id = None

    async def set_overheated(self, worker_id: str) -> None:
        async with self._lock:
            conn = self._workers.get(worker_id)
            if conn:
                conn.status = "overheated"
                conn.current_task_id = None

    async def pick_idle(self) -> WorkerConnection | None:
        """Выбрать idle-воркера с максимальным весом (не overheated)."""
        async with self._lock:
            idle = [
                w
                for w in self._workers.values()
                if w.status == "idle" and w.current_task_id is None
            ]
            if not idle:
                return None
            idle.sort(key=lambda w: w.weight, reverse=True)
            return idle[0]

    async def stale_busy(self, timeout_sec: float) -> list[WorkerConnection]:
        """Воркеры без heartbeat дольше timeout (для grace requeue)."""
        now = datetime.now(timezone.utc)
        async with self._lock:
            out = []
            for w in self._workers.values():
                age = (now - w.last_heartbeat).total_seconds()
                if age >= timeout_sec and w.current_task_id:
                    out.append(w)
            return out

    async def find_by_task(self, task_id: str) -> WorkerConnection | None:
        async with self._lock:
            for w in self._workers.values():
                if w.current_task_id == task_id:
                    return w
            return None

    async def list_snapshot(self) -> list[dict[str, Any]]:
        async with self._lock:
            return [
                {
                    "worker_id": w.worker_id,
                    "status": w.status,
                    "weight": w.weight,
                    "current_task_id": w.current_task_id,
                    "last_heartbeat": w.last_heartbeat.isoformat(),
                    "version": w.version,
                }
                for w in self._workers.values()
            ]


worker_hub = WorkerHub()
