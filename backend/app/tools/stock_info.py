"""工具: 股票基本信息查询"""
import tushare as ts
from langchain_core.tools import tool

from backend.app.core.cache import cache_tool
from backend.app.core.config import get_settings
from backend.app.core.logger import logger


@tool
@cache_tool(ttl=86400)  # 基本信息变动极少, 缓存 1 天
def get_stock_info(ts_code: str) -> str:
    """查询 A 股股票基本信息(名称、行业、上市日期等)。ts_code 格式如 '000001.SZ'。
    若用户给的是中文名而非代码, 应先用 lookup_ts_code 取得 ts_code。
    """
    try:
        pro = ts.pro_api(get_settings().tushare_token)
        df = pro.stock_basic(
            ts_code=ts_code,
            fields="ts_code,name,industry,market,list_date,area",
        )
        if df.empty:
            return f"未找到股票 {ts_code} 的信息"
        r = df.iloc[0]
        return (
            f"股票代码: {r['ts_code']}\n"
            f"股票名称: {r['name']}\n"
            f"所属行业: {r['industry']}\n"
            f"市场板块: {r['market']}\n"
            f"所属地区: {r.get('area', '未知')}\n"
            f"上市日期: {r['list_date']}"
        )
    except Exception as e:
        logger.error(f"get_stock_info({ts_code}) 失败: {e}")
        return f"查询失败: {e}"
