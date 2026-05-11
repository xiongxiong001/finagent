"""统一日志 - 基于 loguru"""
import sys
from loguru import logger

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
           "<level>{message}</level>",
    level="DEBUG",
    colorize=True,
)
logger.add(
    "logs/finagent.log",
    rotation="100 MB",
    retention="7 days",
    level="INFO",
    encoding="utf-8",
)

__all__ = ["logger"]