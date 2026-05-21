"""工具: 财务指标查询"""
from langchain_core.tools import tool

from backend.app.core.cache import cache_tool
from backend.app.datasource import get_datasource


@tool
@cache_tool(ttl=86400)
def get_financial_report(ts_code: str, period: str) -> str:
    """查询 A 股公司核心财务指标(ROE、净利润率、毛利率、资产负债率等)。
    ts_code 格式如 '300750.SZ', period 格式 'YYYYMMDD', 如 '20231231' 表示 2023 年报。
    注意: period 必须是季末日期 (0331/0630/0930/1231)。
    """
    return get_datasource().get_financial_report(ts_code, period)
