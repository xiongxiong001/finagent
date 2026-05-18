"""工具: 股价行情查询 (智能版)

输出策略 (按跨度自适应):
- 1 天 (start == end): 单日快照
- 2~10 天: 逐日列表
- 11+ 天: 区间汇总 + 最后 5 个交易日明细
"""
from datetime import datetime

import tushare as ts
from langchain_core.tools import tool

from backend.app.core.cache import cache_tool
from backend.app.core.config import get_settings
from backend.app.core.logger import logger


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y%m%d")


def _format_snapshot(row) -> str:
    return (
        f"交易日: {row['trade_date']}\n"
        f"  开盘: {row['open']}  最高: {row['high']}  最低: {row['low']}  收盘: {row['close']}\n"
        f"  涨跌幅: {row['pct_chg']}%   成交量: {row['vol']:.0f} 手   成交额: {row['amount']:.0f} 千元"
    )


def _format_daily_list(df) -> str:
    lines = []
    # Tushare 返回的是按日期倒序, 这里翻转成正序更直观
    df_ordered = df.iloc[::-1]
    for _, r in df_ordered.iterrows():
        lines.append(
            f"{r['trade_date']}: 收{r['close']:>7.2f}  涨跌{r['pct_chg']:>6.2f}%  量{r['vol']:>10.0f}"
        )
    return "\n".join(lines)


def _format_summary(df) -> str:
    """区间汇总: 起止价/累计涨跌/区间高低/均价/总成交"""
    df_ordered = df.iloc[::-1]   # 正序
    first = df_ordered.iloc[0]
    last = df_ordered.iloc[-1]
    period_chg = (last["close"] / first["pre_close"] - 1) * 100 if first.get("pre_close") else None
    high = df["high"].max()
    low = df["low"].min()
    avg_close = df["close"].mean()
    total_amount = df["amount"].sum() / 10000  # 千元 -> 万元

    lines = [
        f"区间: {first['trade_date']} ~ {last['trade_date']} ({len(df)} 个交易日)",
        f"  起始价: {first['open']:.2f}   收盘价: {last['close']:.2f}",
    ]
    if period_chg is not None:
        lines.append(f"  累计涨跌幅: {period_chg:+.2f}%")
    lines.extend([
        f"  区间最高: {high:.2f}   最低: {low:.2f}   均价: {avg_close:.2f}",
        f"  累计成交额: {total_amount:.0f} 万元",
        "",
        "最近 5 个交易日:",
    ])
    summary = "\n".join(lines) + "\n"
    last5 = df_ordered.tail(5)
    summary += "\n".join(
        f"  {r['trade_date']}: 收{r['close']:>7.2f}  涨跌{r['pct_chg']:>6.2f}%"
        for _, r in last5.iterrows()
    )
    return summary


@tool
@cache_tool(ttl=300)  # 盘中 5 分钟, 盘后失效再拉一次也无所谓
def get_stock_price(ts_code: str, start_date: str, end_date: str) -> str:
    """查询 A 股历史日行情。
    ts_code 格式如 '300750.SZ',日期格式 'YYYYMMDD'。
    根据日期跨度自适应输出:
      - 1 天: 单日详细快照
      - 2~10 天: 逐日列表
      - 11+ 天: 区间汇总 + 最近 5 个交易日明细
    """
    try:
        pro = ts.pro_api(get_settings().tushare_token)
        df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df.empty:
            return f"未找到 {ts_code} 在 {start_date}~{end_date} 的行情数据 (可能是停牌或日期无效)"

        # 决定输出粒度
        try:
            span_days = (_parse_date(end_date) - _parse_date(start_date)).days
        except ValueError:
            span_days = len(df)

        if span_days == 0 or len(df) == 1:
            return _format_snapshot(df.iloc[0])
        if len(df) <= 10:
            return _format_daily_list(df)
        return _format_summary(df)

    except Exception as e:
        logger.error(f"get_stock_price({ts_code}) 失败: {e}")
        return f"查询失败: {e}"
