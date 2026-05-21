"""工具: 股价行情查询"""
from langchain_core.tools import tool

from backend.app.core.cache import cache_tool
from backend.app.datasource import get_datasource


@tool
@cache_tool(ttl=300)
def get_stock_price(ts_code: str, start_date: str, end_date: str) -> str:
    """查询 A 股历史日行情。
    ts_code 格式如 '300750.SZ', 日期格式 'YYYYMMDD'。
    根据日期跨度自适应输出:
      - 1 天: 单日详细快照
      - 2~10 天: 逐日列表
      - 11+ 天: 区间汇总 + 最近 5 个交易日明细
    """
    return get_datasource().get_stock_price(ts_code, start_date, end_date)
