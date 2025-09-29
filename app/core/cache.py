from redis import asyncio as aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

def init_cache():
    redis = aioredis.from_url("redis://redis", encoding="utf-8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")

async def close_cache():
    await FastAPICache.clear()