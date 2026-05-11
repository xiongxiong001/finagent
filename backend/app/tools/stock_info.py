"""工具 1/5：股票基本信息查询"""
import tushare as ts
from langchain_core.tools import tool
from backend.app.core.config import get_settings
from backend.app.core.logger import logger


@tool
def get_stock_info(ts_code: str) -> str:
    """查询A股股票基本信息（名称、行业、上市日期等）。ts_code 格式如 '000001.SZ'"""
    try:
        pro = ts.pro_api(get_settings().tushare_token)
        df = pro.stock_basic(
            ts_code=ts_code,
            fields="ts_code,name,industry,market,list_date",
        )
        if df.empty:
            return f"未找到股票 {ts_code} 的信息"
        r = df.iloc[0]
        return (
            f"股票代码: {r['ts_code']}\n"
            f"股票名称: {r['name']}\n"
            f"所属行业: {r['industry']}\n"
            f"市场板块: {r['market']}\n"
            f"上市日期: {r['list_date']}"
        )
    except Exception as e:
        logger.error(f"get_stock_info({ts_code}) 失败: {e}")
        return f"查询失败: {e}"
