import asyncio

import pytest

from app.clients.keypool import KeyPool, KeyPoolExhausted


def test_round_robin_spreads_load():
    pool = KeyPool.from_values(["a", "b", "c"])
    got = [asyncio.run(pool.acquire()) for _ in range(6)]
    assert got == ["a", "b", "c", "a", "b", "c"]


def test_quota_429_cools_key_and_rotates_past_it():
    async def go():
        pool = KeyPool.from_values(["a", "b"])
        k = await pool.acquire()
        await pool.report(k, 429)
        # 'a' is cooling; every subsequent acquire must skip it.
        return [await pool.acquire() for _ in range(4)]

    assert set(asyncio.run(go())) == {"b"}


def test_expired_ephemeral_token_401_is_evicted():
    async def go():
        pool = KeyPool.from_values(["durable", "ephemeral"])
        await pool.report("ephemeral", 401)
        return [await pool.acquire() for _ in range(3)]

    assert set(asyncio.run(go())) == {"durable"}


def test_403_also_evicts():
    async def go():
        pool = KeyPool.from_values(["a", "b"])
        await pool.report("b", 403)
        return [await pool.acquire() for _ in range(3)]

    assert set(asyncio.run(go())) == {"a"}


def test_all_keys_dead_raises_rather_than_hanging():
    async def go():
        pool = KeyPool.from_values(["a", "b"])
        await pool.report("a", 429)
        await pool.report("b", 429)
        await pool.acquire()

    with pytest.raises(KeyPoolExhausted, match="all 2 keys cooling"):
        asyncio.run(go())


def test_success_clears_failure_count():
    async def go():
        pool = KeyPool.from_values(["a"])
        await pool.report("a", 429)
        await pool.report("a", 200)
        return pool.keys[0].failures

    assert asyncio.run(go()) == 0


def test_stats_never_leak_full_key():
    secret = "AIzaSyVERYSECRETKEYVALUE1234"
    pool = KeyPool.from_values([secret])
    blob = repr(pool.stats())
    assert secret not in blob
    assert pool.stats()[0]["live"] is True


def test_empty_pool_rejected_at_construction():
    with pytest.raises(ValueError, match="at least one key"):
        KeyPool.from_values([])
