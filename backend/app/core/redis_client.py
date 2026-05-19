"""Redis 客户端 - 单例 + 自动重连"""
from functools import lru_cache
import redis.asyncio as aioredis

from backend.app.core.config import get_settings


@lru_cache
def get_redis() -> aioredis.Redis:
    """返回单例 Redis 客户端 (异步)"""
    return aioredis.from_url(
        get_settings().redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
