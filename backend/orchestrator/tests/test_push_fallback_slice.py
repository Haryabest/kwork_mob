"""Отложенный email-fallback push §3.4.3."""

import asyncio

from app.services import push_fallback


class _FakeRedis:
    def __init__(self):
        self.z: dict[str, float] = {}
        self.h: dict[str, str] = {}

    async def hset(self, _hash, key, val):
        self.h[key] = val

    async def zadd(self, _zset, mapping):
        self.z.update(mapping)

    async def zrangebyscore(self, _zset, lo, hi, start=0, num=100):
        keys = [k for k, s in self.z.items() if lo <= s <= hi]
        return keys[start : start + num]

    async def hget(self, _hash, key):
        return self.h.get(key)

    async def zrem(self, _zset, key):
        self.z.pop(key, None)

    async def hdel(self, _hash, key):
        self.h.pop(key, None)


class _Notif:
    def __init__(self, read_at):
        self.read_at = read_at


class _FakeDB:
    def __init__(self, read_at=None):
        self._read_at = read_at

    async def get(self, _model, _id):
        return _Notif(self._read_at)


def test_schedule_then_process_sends_when_unread():
    async def _run():
        redis = _FakeRedis()
        await push_fallback.schedule(
            redis,
            key="k1",
            notif_id=1,
            user_id=10,
            email="u@example.com",
            title="T",
            body="B",
            delay=0,
        )
        res = await push_fallback.process_due(_FakeDB(read_at=None), redis, now=10_000_000_000)
        return res, redis

    res, redis = asyncio.run(_run())
    assert res["sent"] == 1
    assert redis.z == {} and redis.h == {}


def test_process_skips_when_already_read():
    import datetime

    async def _run():
        redis = _FakeRedis()
        await push_fallback.schedule(
            redis,
            key="k2",
            notif_id=2,
            user_id=11,
            email="u@example.com",
            title="T",
            body="B",
            delay=0,
        )
        return await push_fallback.process_due(
            _FakeDB(read_at=datetime.datetime.now()), redis, now=10_000_000_000
        )

    res = asyncio.run(_run())
    assert res["sent"] == 0
    assert res["skipped"] == 1


def test_default_delay_constant():
    assert push_fallback.DEFAULT_DELAY_SEC == 300
