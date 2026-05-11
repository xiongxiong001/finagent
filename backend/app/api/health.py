"""健康检查 - 验证所有依赖服务可达"""
import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.core.logger import logger
from backend.app.models.health import HealthStatus

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """检查 Redis + Qdrant 连通性"""
    settings = get_settings()
    services: dict[str, str] = {}

    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        services["redis"] = "ok"
    except Exception as e:
        logger.error(f"Redis 检查失败: {e}")
        services["redis"] = f"error: {type(e).__name__}"

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.qdrant_url}/")
            services["qdrant"] = "ok" if resp.status_code == 200 else f"error: {resp.status_code}"
    except Exception as e:
        logger.error(f"Qdrant 检查失败: {e}")
        services["qdrant"] = f"error: {type(e).__name__}"

    all_ok = all(v == "ok" for v in services.values())
    return HealthStatus(
        status="healthy" if all_ok else "degraded",
        version=settings.app_version,
        services=services,
    )