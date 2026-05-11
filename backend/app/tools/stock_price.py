"""工具 2/5：股价历史行情查询"""
import tushare as ts
from langchain_core.tools import tool
from backend.app.core.config import get_settings
from backend.app.core.logger import logger


@tool
def get_stock_price(ts_code: str, start_date: str, end_date: str) -> str:
    """查询A股历史日行情（收盘价、涨跌幅、成交量）。
    ts_code 格式如 '000001.SZ'，日期格式 'YYYYMMDD'。
    """
    try:
        pro = ts.pro_api(get_settings().tushare_token)
        df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df.empty:
            return f"未找到 {ts_code} 在 {start_date}~{end_date} 的行情数据"
        r = df.iloc[0]
        return (
            f"最新交易日: {r['trade_date']}\n"
            f"收盘价:    {r['close']}\n"
            f"涨跌幅:    {r['pct_chg']}%\n"
            f"成交量:    {r['vol']} 手\n"
            f"成交额:    {r['amount']} 千元"
        )
    except Exception as e:
        logger.error(f"get_stock_price({ts_code}) 失败: {e}")
        return f"查询失败: {e}"
