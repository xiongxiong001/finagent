"""工具: 股票基本信息查询"""
from langchain_core.tools import tool

from backend.app.core.cache import cache_tool
from backend.app.datasource import get_datasource


@tool
@cache_tool(ttl=86400)
def get_stock_info(ts_code: str) -> str:
    """查询 A 股股票基本信息(名称、行业、上市日期等)。ts_code 格式如 '000001.SZ'。
    若用户给的是中文名而非代码, 应先用 lookup_ts_code 取得 ts_code。
    """
    return get_datasource().get_stock_info(ts_code)
