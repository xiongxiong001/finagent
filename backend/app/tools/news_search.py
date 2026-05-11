"""工具 4/5：财经新闻搜索"""
import tushare as ts
from langchain_core.tools import tool
from backend.app.core.config import get_settings
from backend.app.core.logger import logger


@tool
def search_news(keyword: str, start_date: str, end_date: str) -> str:
    """搜索A股相关财经新闻。keyword 为关键词，日期格式 'YYYYMMDD'。"""
    try:
        pro = ts.pro_api(get_settings().tushare_token)
        df = pro.news(src="sina", start_date=start_date, end_date=end_date)
        if df.empty:
            return "未找到相关新闻"
        mask = df["title"].str.contains(keyword, na=False)
        matched = df[mask] if mask.any() else df
        rows = matched.head(5)
        lines = [
            f"[{r.get('datetime', '')}] {r.get('title', '')}"
            for _, r in rows.iterrows()
        ]
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"search_news({keyword}) 失败: {e}")
        return f"查询失败: {e}"