"""工具调用缓存装饰器

设计要点:
- LangChain 的 @tool 装饰的工具是同步函数, 这里用同步 redis-py
- key = "tool:{func_name}:{hash(args)}", 避免参数顺序/类型差异引起 cache miss
- 失败时降级到直接调用, 不让缓存层成为故障点
"""
import hashlib
import json
from functools import wraps
from typing import Callable

import redis

from backend.app.core.config import get_settings
from backend.app.core.logger import logger


_sync_redis: redis.Redis | None = None


def _get_sync_redis() -> redis.Redis:
    """同步 Redis 客户端 (工具是同步函数, 不能用 async)"""
    global _sync_redis
    if _sync_redis is None:
        _sync_redis = redis.from_url(
            get_settings().redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _sync_redis


def _make_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """生成稳定的 cache key"""
    payload = json.dumps(
        {"args": args, "kwargs": kwargs},
        sort_keys=True,
        default=str,
        ensure_ascii=False,
    )
    digest = hashlib.md5(payload.encode("utf-8")).hexdigest()[:16]
    return f"tool:{func_name}:{digest}"


def cache_tool(ttl: int):
    """同步函数的 Redis 缓存装饰器

    用法:
        @tool
        @cache_tool(ttl=300)
        def get_stock_price(...): ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = _make_key(func.__name__, args, kwargs)
            try:
                client = _get_sync_redis()
                cached = client.get(key)
                if cached is not None:
                    logger.debug(f"[cache hit] {key}")
                    return cached
            except Exception as e:
                logger.warning(f"[cache read error] {e}, 降级直接调用")

            result = func(*args, **kwargs)

            # 失败/未找到 这类回包不入缓存, 避免缓存错误
            if isinstance(result, str) and (
                result.startswith("查询失败")
                or result.startswith("未找到")
                or result.startswith("检索失败")
            ):
                return result

            try:
                _get_sync_redis().setex(key, ttl, result)
            except Exception as e:
                logger.warning(f"[cache write error] {e}")

            return result

        return wrapper

    return decorator
