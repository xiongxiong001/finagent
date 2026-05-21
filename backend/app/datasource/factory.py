"""数据源工厂

根据配置 DATA_SOURCE 返回对应实现的单例。
扩展: 新增数据源时在此注册, 工具层无需改动。
"""
from functools import lru_cache

from backend.app.core.config import get_settings
from backend.app.core.logger import logger
from backend.app.datasource.base import StockDataSource

_REGISTRY: dict[str, str] = {
    "tushare": "backend.app.datasource.tushare_source.TushareDataSource",
    "akshare": "backend.app.datasource.akshare_source.AKShareDataSource",
}


@lru_cache(maxsize=1)
def get_datasource() -> StockDataSource:
    name = get_settings().data_source.lower()
    class_path = _REGISTRY.get(name)
    if not class_path:
        available = list(_REGISTRY.keys())
        raise ValueError(f"未知数据源 '{name}', 可选: {available}")

    module_path, class_name = class_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    logger.info(f"数据源: {name} ({class_path})")
    return cls()
