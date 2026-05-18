"""工具: 财务指标查询"""
import tushare as ts
from langchain_core.tools import tool

from backend.app.core.cache import cache_tool
from backend.app.core.config import get_settings
from backend.app.core.logger import logger


@tool
@cache_tool(ttl=86400)  # 季报频率, 缓存 1 天足够
def get_financial_report(ts_code: str, period: str) -> str:
    """查询 A 股公司核心财务指标(ROE、净利润率、毛利率、资产负债率等)。
    ts_code 格式如 '300750.SZ',period 格式 'YYYYMMDD',如 '20231231' 表示 2023 年报。
    注意: period 必须是季末日期 (0331/0630/0930/1231)。
    """
    try:
        pro = ts.pro_api(get_settings().tushare_token)
        df = pro.fina_indicator(
            ts_code=ts_code,
            period=period,
            fields="ts_code,ann_date,eps,roe,netprofit_margin,grossprofit_margin,debt_to_assets,current_ratio,quick_ratio",
        )
        if df.empty:
            return f"未找到 {ts_code} 报告期 {period} 的财务数据 (请确认是季末日期)"
        r = df.iloc[0]
        return (
            f"报告期:       {period}\n"
            f"公告日期:     {r.get('ann_date', 'N/A')}\n"
            f"每股收益(EPS):{r.get('eps', 'N/A')}\n"
            f"ROE:          {r.get('roe', 'N/A')}%\n"
            f"净利润率:     {r.get('netprofit_margin', 'N/A')}%\n"
            f"毛利率:       {r.get('grossprofit_margin', 'N/A')}%\n"
            f"资产负债率:   {r.get('debt_to_assets', 'N/A')}%\n"
            f"流动比率:     {r.get('current_ratio', 'N/A')}\n"
            f"速动比率:     {r.get('quick_ratio', 'N/A')}"
        )
    except Exception as e:
        logger.error(f"get_financial_report({ts_code}, {period}) 失败: {e}")
        return f"查询失败: {e}"
