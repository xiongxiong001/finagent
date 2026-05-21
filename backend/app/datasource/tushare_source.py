"""Tushare 数据源实现

依赖接口:
- stock_basic: 免费 (lookup / info / news 的名称解析)
- daily / fina_indicator / news: 需 2000+ 积分
积分不足时错误透传给调用方。
"""
import json
from datetime import datetime

import tushare as ts

from backend.app.core.cache import _get_sync_redis
from backend.app.core.config import get_settings
from backend.app.core.logger import logger
from backend.app.datasource.base import StockDataSource

_NAME_MAP_KEY = "stock_name_map:v1"


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y%m%d")


def _to_datetime_str(date_str: str, end_of_day: bool = False) -> str:
    formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return f"{formatted} 23:59:59" if end_of_day else f"{formatted} 00:00:00"


def _format_snapshot(row) -> str:
    return (
        f"交易日: {row['trade_date']}\n"
        f"  开盘: {row['open']}  最高: {row['high']}  最低: {row['low']}  收盘: {row['close']}\n"
        f"  涨跌幅: {row['pct_chg']}%   成交量: {row['vol']:.0f} 手   成交额: {row['amount']:.0f} 千元"
    )


def _format_daily_list(df) -> str:
    lines = []
    for _, r in df.iloc[::-1].iterrows():
        lines.append(
            f"{r['trade_date']}: 收{r['close']:>7.2f}  涨跌{r['pct_chg']:>6.2f}%  量{r['vol']:>10.0f}"
        )
    return "\n".join(lines)


def _format_summary(df) -> str:
    df_ord = df.iloc[::-1]
    first, last = df_ord.iloc[0], df_ord.iloc[-1]
    period_chg = (last["close"] / first["pre_close"] - 1) * 100 if first.get("pre_close") else None
    lines = [
        f"区间: {first['trade_date']} ~ {last['trade_date']} ({len(df)} 个交易日)",
        f"  起始价: {first['open']:.2f}   收盘价: {last['close']:.2f}",
    ]
    if period_chg is not None:
        lines.append(f"  累计涨跌幅: {period_chg:+.2f}%")
    lines += [
        f"  区间最高: {df['high'].max():.2f}   最低: {df['low'].min():.2f}   均价: {df['close'].mean():.2f}",
        f"  累计成交额: {df['amount'].sum() / 10000:.0f} 万元",
        "",
        "最近 5 个交易日:",
    ]
    lines += [
        f"  {r['trade_date']}: 收{r['close']:>7.2f}  涨跌{r['pct_chg']:>6.2f}%"
        for _, r in df_ord.tail(5).iterrows()
    ]
    return "\n".join(lines)


class TushareDataSource(StockDataSource):

    def _pro(self):
        return ts.pro_api(get_settings().tushare_token)

    def _load_stock_list(self) -> list[dict]:
        """全量股票列表，Redis 缓存 1 天"""
        try:
            cached = _get_sync_redis().get(_NAME_MAP_KEY)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"读取股票列表缓存失败: {e}")

        df = self._pro().stock_basic(exchange="", list_status="L", fields="ts_code,name,industry")
        records = df.to_dict("records")
        try:
            _get_sync_redis().setex(
                _NAME_MAP_KEY,
                get_settings().cache_ttl_name_map,
                json.dumps(records, ensure_ascii=False),
            )
        except Exception as e:
            logger.warning(f"写入股票列表缓存失败: {e}")
        return records

    def lookup_stock_code(self, name: str) -> str:
        try:
            stocks = self._load_stock_list()
            exact = [s for s in stocks if s["name"] == name]
            if exact:
                s = exact[0]
                return f"{s['name']} ({s['ts_code']}, 行业: {s.get('industry', '未知')})"
            contains = [s for s in stocks if name in s["name"]][:5]
            if contains:
                lines = [f"{s['name']} ({s['ts_code']}, 行业: {s.get('industry', '未知')})" for s in contains]
                return "找到多个候选，请确认具体哪一个:\n" + "\n".join(lines)
            return f"未找到名称为「{name}」的 A 股股票"
        except Exception as e:
            logger.error(f"[Tushare] lookup_stock_code({name}) 失败: {e}")
            return f"查询失败: {e}"

    def get_stock_info(self, ts_code: str) -> str:
        try:
            df = self._pro().stock_basic(ts_code=ts_code, fields="ts_code,name,industry,market,list_date,area")
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
            logger.error(f"[Tushare] get_stock_info({ts_code}) 失败: {e}")
            return f"查询失败: {e}"

    def get_stock_price(self, ts_code: str, start_date: str, end_date: str) -> str:
        try:
            df = self._pro().daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df.empty:
                return f"未找到 {ts_code} 在 {start_date}~{end_date} 的行情数据"
            try:
                span = (_parse_date(end_date) - _parse_date(start_date)).days
            except ValueError:
                span = len(df)
            if span == 0 or len(df) == 1:
                return _format_snapshot(df.iloc[0])
            if len(df) <= 10:
                return _format_daily_list(df)
            return _format_summary(df)
        except Exception as e:
            logger.error(f"[Tushare] get_stock_price({ts_code}) 失败: {e}")
            return f"查询失败: {e}"

    def get_financial_report(self, ts_code: str, period: str) -> str:
        try:
            df = self._pro().fina_indicator(
                ts_code=ts_code,
                period=period,
                fields="ts_code,ann_date,eps,roe,netprofit_margin,grossprofit_margin,debt_to_assets,current_ratio,quick_ratio",
            )
            if df.empty:
                return f"未找到 {ts_code} 报告期 {period} 的财务数据"
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
            logger.error(f"[Tushare] get_financial_report({ts_code}, {period}) 失败: {e}")
            return f"查询失败: {e}"

    def search_news(self, ts_code: str, start_date: str, end_date: str) -> str:
        try:
            # ts_code → 公司名, 用作新闻关键词
            name_df = self._pro().stock_basic(ts_code=ts_code, fields="ts_code,name")
            keyword = name_df.iloc[0]["name"] if not name_df.empty else ts_code.split(".")[0]

            df = self._pro().news(
                src="sina",
                start_date=_to_datetime_str(start_date),
                end_date=_to_datetime_str(end_date, end_of_day=True),
            )
            if df.empty:
                return f"在 {start_date}~{end_date} 期间未找到任何新闻"

            title_hit = df["title"].fillna("").str.contains(keyword, na=False)
            content_hit = (
                df["content"].fillna("").str.contains(keyword, na=False)
                if "content" in df.columns
                else title_hit
            )
            matched = df[title_hit | content_hit]
            if matched.empty:
                return f"在 {start_date}~{end_date} 期间未找到与「{keyword}」相关的新闻"

            lines = []
            for _, r in matched.head(5).iterrows():
                content = (r.get("content", "") or "")[:120]
                lines.append(f"[{r.get('datetime', '')}] {r.get('title', '')}\n  {content}...")
            return "\n\n".join(lines)
        except Exception as e:
            logger.error(f"[Tushare] search_news({ts_code}) 失败: {e}")
            return f"查询失败: {e}"
