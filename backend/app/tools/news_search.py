"""工具: 个股财经新闻查询"""
from langchain_core.tools import tool

from backend.app.core.cache import cache_tool
from backend.app.datasource import get_datasource


@tool
@cache_tool(ttl=300)
def search_news(ts_code: str, start_date: str, end_date: str) -> str:
    """查询 A 股个股相关财经新闻。
    ts_code 格式如 '002594.SZ' (若用户给的是中文名, 须先调 lookup_ts_code 转换)。
    start_date / end_date: 'YYYYMMDD' 格式。
    返回最多 8 条相关新闻。
    """
    return get_datasource().search_news(ts_code, start_date, end_date)
