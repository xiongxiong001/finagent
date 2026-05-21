"""AKShare 数据源实现

接口选型原则: 避开不稳定的东方财富实时行情接口, 优先使用交易所官网和网易财经。
  - 股票列表/名称查询: AKShare stock_info_a_code_name (稳定)
  - 基本信息: 深交所/上交所官网 (不依赖东方财富)
  - 历史行情: 网易财经 163 (不依赖东方财富)
  - 财务数据: 同花顺 (稳定)
  - 新闻:     东方财富 stock_news_em (失败时返回空)
"""
import json

import akshare as ak

from backend.app.core.cache import _get_sync_redis
from backend.app.core.config import get_settings
from backend.app.core.logger import logger
from backend.app.datasource.base import StockDataSource

_AK_NAME_MAP_KEY = "ak_stock_name_map:v1"


def _to_symbol(ts_code: str) -> str:
    """'002594.SZ' -> '002594'"""
    return ts_code.split(".")[0]


def _exchange(ts_code: str) -> str:
    """'002594.SZ' -> 'SZ'"""
    return ts_code.split(".")[-1].upper() if "." in ts_code else ""


def _code_to_ts_code(code: str) -> str:
    """6位代码 → ts_code，按前缀推断交易所"""
    if code.startswith(("6", "9", "5")):
        return f"{code}.SH"
    if code.startswith(("8", "4")):
        return f"{code}.BJ"
    return f"{code}.SZ"


def _yyyymmdd_to_dash(date_str: str) -> str:
    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"


def _to_tx_symbol(ts_code: str) -> str:
    """'000001.SZ' -> 'sz000001', '600000.SH' -> 'sh600000'"""
    code = _to_symbol(ts_code)
    exch = _exchange(ts_code).lower()
    return f"{exch}{code}" if exch in ("sh", "sz") else f"sz{code}"


# ── 股票列表缓存 ────────────────────────────────────────────────────────────

def _load_ak_stock_list() -> list[dict]:
    """全量 A 股列表 (code, name)，Redis 缓存 1 天"""
    try:
        cached = _get_sync_redis().get(_AK_NAME_MAP_KEY)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"读取 AKShare 股票列表缓存失败: {e}")

    df = ak.stock_info_a_code_name()
    records = df.to_dict("records")
    try:
        _get_sync_redis().setex(
            _AK_NAME_MAP_KEY,
            get_settings().cache_ttl_name_map,
            json.dumps(records, ensure_ascii=False),
        )
    except Exception as e:
        logger.warning(f"写入 AKShare 股票列表缓存失败: {e}")
    return records


# ── 行情格式化 (兼容网易163列名) ──────────────────────────────────────────────

def _normalize_tx(df):
    """腾讯行情 (英文列名) → 统一中文列名，并补算涨跌幅"""
    df = df.copy().rename(columns={
        "date": "日期", "open": "开盘", "close": "收盘",
        "high": "最高", "low": "最低", "amount": "成交量",
    })
    df["涨跌幅"] = df["收盘"].pct_change() * 100
    df["成交额"] = df["收盘"] * df["成交量"] * 100   # 手→股→估算成交额
    df["涨跌幅"] = df["涨跌幅"].fillna(0)
    return df.reset_index(drop=True)


def _fmt_snapshot(row) -> str:
    return (
        f"交易日: {row['日期']}\n"
        f"  开盘: {row['开盘']}  最高: {row['最高']}  最低: {row['最低']}  收盘: {row['收盘']}\n"
        f"  涨跌幅: {float(row['涨跌幅']):.2f}%   成交量: {float(row['成交量']):,.0f} 手"
    )


def _fmt_daily_list(df) -> str:
    return "\n".join(
        f"{r['日期']}: 收{float(r['收盘']):>7.2f}  涨跌{float(r['涨跌幅']):>6.2f}%  量{float(r['成交量']):>10.0f}"
        for _, r in df.iterrows()
    )


def _fmt_summary(df) -> str:
    first, last = df.iloc[0], df.iloc[-1]
    period_chg = (float(last["收盘"]) / float(first["开盘"]) - 1) * 100
    lines = [
        f"区间: {first['日期']} ~ {last['日期']} ({len(df)} 个交易日)",
        f"  起始价: {float(first['开盘']):.2f}   收盘价: {float(last['收盘']):.2f}",
        f"  累计涨跌幅: {period_chg:+.2f}%",
        f"  区间最高: {float(df['最高'].max()):.2f}   最低: {float(df['最低'].min()):.2f}   均价: {float(df['收盘'].mean()):.2f}",
        "",
        "最近 5 个交易日:",
    ]
    lines += [
        f"  {r['日期']}: 收{float(r['收盘']):>7.2f}  涨跌{float(r['涨跌幅']):>6.2f}%"
        for _, r in df.tail(5).iterrows()
    ]
    return "\n".join(lines)


# ── 数据源实现 ──────────────────────────────────────────────────────────────

class AKShareDataSource(StockDataSource):

    def lookup_stock_code(self, name: str) -> str:
        try:
            stocks = _load_ak_stock_list()
            exact = [s for s in stocks if s["name"] == name]
            if exact:
                s = exact[0]
                return f"{s['name']} ({_code_to_ts_code(s['code'])})"
            contains = [s for s in stocks if name in s["name"]][:5]
            if contains:
                lines = [f"{s['name']} ({_code_to_ts_code(s['code'])})" for s in contains]
                return "找到多个候选，请确认具体哪一个:\n" + "\n".join(lines)
            return f"未找到名称为「{name}」的 A 股股票，请确认拼写或直接提供股票代码"
        except Exception as e:
            logger.error(f"[AKShare] lookup_stock_code({name}) 失败: {e}")
            return f"查询失败: {e}"

    def get_stock_info(self, ts_code: str) -> str:
        """使用深交所/上交所官网 API，不依赖东方财富"""
        symbol = _to_symbol(ts_code)
        exch = _exchange(ts_code)
        try:
            if exch == "SZ":
                df = ak.stock_info_sz_name_code()   # 无需 indicator 参数
                match = df[df["A股代码"].astype(str).str.zfill(6) == symbol]
                if not match.empty:
                    r = match.iloc[0]
                    return (
                        f"股票代码: {ts_code}\n"
                        f"股票名称: {r.get('A股简称', 'N/A')}\n"
                        f"所属行业: {r.get('所属行业', 'N/A')}\n"
                        f"上市日期: {r.get('A股上市日期', 'N/A')}"
                    )
            elif exch == "SH":
                df = ak.stock_info_sh_name_code(indicator="主板A股")
                match = df[df["证券代码"].astype(str).str.zfill(6) == symbol]
                if not match.empty:
                    r = match.iloc[0]
                    return (
                        f"股票代码: {ts_code}\n"
                        f"股票名称: {r.get('证券简称', 'N/A')}\n"
                        f"上市日期: {r.get('上市日期', 'N/A')}"
                    )
        except Exception as e:
            logger.warning(f"[AKShare] get_stock_info 交易所接口失败，降级到名称库: {e}")

        # 降级：从已缓存的名称列表返回基本信息
        try:
            stocks = _load_ak_stock_list()
            matches = [s for s in stocks if s["code"] == symbol]
            if matches:
                exch_name = {"SH": "上交所", "SZ": "深交所", "BJ": "北交所"}.get(exch, "")
                return f"股票代码: {ts_code}\n股票名称: {matches[0]['name']}\n交易所: {exch_name}"
        except Exception:
            pass

        return f"未找到股票 {ts_code} 的信息"

    def get_stock_price(self, ts_code: str, start_date: str, end_date: str) -> str:
        """使用腾讯财经历史行情，不依赖东方财富"""
        try:
            tx_sym = _to_tx_symbol(ts_code)
            df = ak.stock_zh_a_hist_tx(
                symbol=tx_sym,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
            )
            if df.empty:
                return f"未找到 {ts_code} 在 {start_date}~{end_date} 的行情数据"

            df = _normalize_tx(df).sort_values("日期").reset_index(drop=True)
            n = len(df)
            if n == 1:
                return _fmt_snapshot(df.iloc[0])
            if n <= 10:
                return _fmt_daily_list(df)
            return _fmt_summary(df)
        except Exception as e:
            logger.error(f"[AKShare] get_stock_price({ts_code}) 失败: {e}")
            return f"查询失败: {e}"

    def get_financial_report(self, ts_code: str, period: str) -> str:
        """使用同花顺财务数据"""
        try:
            symbol = _to_symbol(ts_code)
            df = ak.stock_financial_abstract_ths(symbol=symbol, indicator="按报告期")
            if df.empty:
                return f"未找到 {ts_code} 的财务数据"

            date_col = df.columns[0]
            target_prefix = f"{period[:4]}-{period[4:6]}"
            mask = df[date_col].astype(str).str.startswith(target_prefix)
            row = df[mask].iloc[0] if mask.any() else df.iloc[0]
            actual_period = row[date_col] if mask.any() else f"{row[date_col]}(最近)"

            lines = [f"报告期: {actual_period}"]
            for col in df.columns[1:]:
                lines.append(f"{col}: {row[col]}")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"[AKShare] get_financial_report({ts_code}, {period}) 失败: {e}")
            return f"查询失败: {e}"

    def search_news(self, ts_code: str, start_date: str, end_date: str) -> str:
        """使用东方财富个股新闻，失败时返回提示而非抛异常"""
        try:
            symbol = _to_symbol(ts_code)
            df = ak.stock_news_em(symbol=symbol)
            if df.empty:
                return f"未找到 {ts_code} 的相关新闻"

            date_col = next((c for c in df.columns if "时间" in c or "date" in c.lower()), None)
            if date_col:
                start_dash = _yyyymmdd_to_dash(start_date)
                end_dash = _yyyymmdd_to_dash(end_date) + " 23:59:59"
                df[date_col] = df[date_col].astype(str)
                df = df[(df[date_col] >= start_dash) & (df[date_col] <= end_dash)]

            if df.empty:
                return f"在 {start_date}~{end_date} 期间未找到 {ts_code} 的相关新闻"

            title_col = next((c for c in df.columns if "标题" in c), df.columns[1])
            content_col = next((c for c in df.columns if "内容" in c), None)

            lines = []
            for _, r in df.head(8).iterrows():
                dt = r.get(date_col, "") if date_col else ""
                title = r.get(title_col, "")
                content = str(r.get(content_col, ""))[:150] if content_col else ""
                entry = f"[{dt}] {title}"
                if content:
                    entry += f"\n  {content}..."
                lines.append(entry)
            return "\n\n".join(lines)
        except Exception as e:
            logger.error(f"[AKShare] search_news({ts_code}) 失败: {e}")
            return f"暂无法获取 {ts_code} 的新闻数据: {e}"
