from backend.app.tools.stock_info import get_stock_info
from backend.app.tools.stock_price import get_stock_price
from backend.app.tools.financial_report import get_financial_report
from backend.app.tools.news_search import search_news
from backend.app.tools.rag_search import search_research_reports

ALL_TOOLS = [
    get_stock_info,
    get_stock_price,
    get_financial_report,
    search_news,
    search_research_reports,
]
