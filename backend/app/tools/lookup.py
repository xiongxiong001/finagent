"""工具: 股票名/别名 -> ts_code

实现思路:
- 启动后首次调用拉全量 (~5000 只 A 股), 缓存到 Redis 1 天
- 模糊匹配: 全等优先, 包含其次
- 别名先做一次映射 ("宁王" -> "宁德时代") 再查
"""
import json

import tushare as ts
from langchain_core.tools import tool

from backend.app.core.cache import _get_sync_redis
from backend.app.core.config import get_settings
from backend.app.core.logger import logger
from backend.app.tools._aliases import resolve_alias


_NAME_MAP_KEY = "stock_name_map:v1"


def _load_or_fetch_stock_list() -> list[dict]:
    """先查 Redis,没有就拉 Tushare 并缓存"""
    try:
        cached = _get_sync_redis().get(_NAME_MAP_KEY)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"读取股票列表缓存失败: {e}")

    pro = ts.pro_api(get_settings().tushare_token)
    df = pro.stock_basic(
        exchange="",
        list_status="L",
        fields="ts_code,name,industry",
    )
    records = df.to_dict("records")

    try:
        _get_sync_redis().setex(
            _NAME_MAP_KEY,
            get_settings().cache_ttl_name_map,
            json.dumps(records, ensure_ascii=False),
        )
    except Exception as e:
        logger.warning(f"写入股票列表缓存失败: {e}")

    return records


@tool
def lookup_ts_code(name: str) -> str:
    """根据股票中文名或常用简称查询 ts_code (如 '宁德时代' -> '300750.SZ')。
    支持模糊匹配和常见别名 (宁王/茅台/招行 等)。
    当用户输入的是中文名而非代码时, 必须先调用此工具拿到 ts_code。
    """
    try:
        resolved = resolve_alias(name)
        stocks = _load_or_fetch_stock_list()

        # 1. 精确匹配
        exact = [s for s in stocks if s["name"] == resolved]
        if exact:
            s = exact[0]
            return f"{s['name']} ({s['ts_code']}, 行业: {s.get('industry', '未知')})"

        # 2. 包含匹配 (前 5 个)
        contains = [s for s in stocks if resolved in s["name"]]
        if contains:
            top = contains[:5]
            lines = [
                f"{s['name']} ({s['ts_code']}, 行业: {s.get('industry', '未知')})"
                for s in top
            ]
            return "找到多个候选,请确认具体哪一个:\n" + "\n".join(lines)

        return f"未找到名称为「{name}」的 A 股股票,请确认拼写或提供股票代码 (如 300750.SZ)"
    except Exception as e:
        logger.error(f"lookup_ts_code({name}) 失败: {e}")
        return f"查询失败: {e}"
