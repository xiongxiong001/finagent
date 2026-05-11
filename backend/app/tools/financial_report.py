"""工具 3/5：财务指标查询"""
import tushare as ts
from langchain_core.tools import tool
from backend.app.core.config import get_settings
from backend.app.core.logger import logger


@tool
def get_financial_report(ts_code: str, period: str) -> str:
    """查询A股公司核心财务指标（ROE、净利润率、毛利率、资产负债率等）。
    ts_code 格式如 '000001.SZ'，period 格式 'YYYYMMDD'，如 '20231231'。
    """
    try:
        pro = ts.pro_api(get_settings().tushare_token)
        df = pro.fina_indicator(
            ts_code=ts_code,
            period=period,
            fields="ts_code,ann_date,eps,roe,netprofit_margin,grossprofit_margin,debt_to_assets",
        )
        if df.empty:
            return f"未找到 {ts_code} 报告期 {period} 的财务数据"
        r = df.iloc[0]
        return (
            f"报告期:     {period}\n"
            f"EPS:        {r.get('eps', 'N/A')}\n"
            f"ROE:        {r.get('roe', 'N/A')}%\n"
            f"净利润率:   {r.get('netprofit_margin', 'N/A')}%\n"
            f"毛利率:     {r.get('grossprofit_margin', 'N/A')}%\n"
            f"资产负债率: {r.get('debt_to_assets', 'N/A')}%"
        )
    except Exception as e:
        logger.error(f"get_financial_report({ts_code}, {period}) 失败: {e}")
        return f"查询失败: {e}"