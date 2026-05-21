"""工具: 股票名/别名 -> ts_code"""
from langchain_core.tools import tool

from backend.app.datasource import get_datasource
from backend.app.tools._aliases import resolve_alias


@tool
def lookup_ts_code(name: str) -> str:
    """根据股票中文名或常用简称查询 ts_code (如 '宁德时代' -> '300750.SZ')。
    支持模糊匹配和常见别名 (宁王/茅台/招行 等)。
    当用户输入的是中文名而非代码时, 必须先调用此工具拿到 ts_code。
    """
    resolved = resolve_alias(name)
    return get_datasource().lookup_stock_code(resolved)
