"""工具: 财经新闻搜索

注意:
- Tushare news 接口按时间窗口拉, 不带关键词参数, 这里拉回来再本地过滤
- 大时间窗会触发频次限制, 这里默认窗口 = 用户传入的 end_date 前后 1 天
- 严格按关键词过滤, 没匹配上就老老实实说没有, 不返回无关新闻
"""
import tushare as ts
from langchain_core.tools import tool

from backend.app.core.cache import cache_tool
from backend.app.core.config import get_settings
from backend.app.core.logger import logger


def _to_datetime_str(date_str: str, end_of_day: bool = False) -> str:
    """'20240115' -> '2024-01-15 00:00:00' 或 '2024-01-15 23:59:59'"""
    if len(date_str) != 8:
        return date_str
    formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return f"{formatted} 23:59:59" if end_of_day else f"{formatted} 00:00:00"


@tool
@cache_tool(ttl=300)  # 新闻 5 分钟
def search_news(keyword: str, start_date: str, end_date: str) -> str:
    """搜索 A 股相关财经新闻。
    keyword: 关键词(公司名、概念名、事件名)
    start_date / end_date: 'YYYYMMDD' 格式
    返回最多 5 条相关新闻; 没匹配上会明确告知,不会返回无关结果。
    """
    try:
        pro = ts.pro_api(get_settings().tushare_token)
        df = pro.news(
            src="sina",
            start_date=_to_datetime_str(start_date),
            end_date=_to_datetime_str(end_date, end_of_day=True),
        )
        if df.empty:
            return f"在 {start_date}~{end_date} 期间未找到任何新闻"

        # 标题 + 正文都搜
        title_hit = df["title"].fillna("").str.contains(keyword, na=False)
        content_hit = df["content"].fillna("").str.contains(keyword, na=False) if "content" in df.columns else title_hit
        mask = title_hit | content_hit
        matched = df[mask]

        if matched.empty:
            return f"在 {start_date}~{end_date} 期间未找到与「{keyword}」相关的新闻"

        rows = matched.head(5)
        lines = []
        for _, r in rows.iterrows():
            dt = r.get("datetime", "")
            title = r.get("title", "")
            content = (r.get("content", "") or "")[:120]
            lines.append(f"[{dt}] {title}\n  {content}...")
        return "\n\n".join(lines)
    except Exception as e:
        logger.error(f"search_news({keyword}) 失败: {e}")
        return f"查询失败: {e}"
