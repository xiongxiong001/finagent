"""数据源抽象接口

新增数据源: 继承 StockDataSource, 实现所有抽象方法, 在 factory.py 注册即可。
"""
from abc import ABC, abstractmethod


class StockDataSource(ABC):

    @abstractmethod
    def lookup_stock_code(self, name: str) -> str:
        """中文名/别名 → ts_code。name 已经过别名解析。"""

    @abstractmethod
    def get_stock_info(self, ts_code: str) -> str:
        """股票基本信息(名称、行业、上市日期等)。ts_code 如 '000001.SZ'。"""

    @abstractmethod
    def get_stock_price(self, ts_code: str, start_date: str, end_date: str) -> str:
        """查询历史日行情。ts_code 如 '300750.SZ', 日期 'YYYYMMDD'。"""

    @abstractmethod
    def get_financial_report(self, ts_code: str, period: str) -> str:
        """查询财务指标。period 为季末日期如 '20231231'。"""

    @abstractmethod
    def search_news(self, ts_code: str, start_date: str, end_date: str) -> str:
        """查询个股相关新闻。ts_code 如 '002594.SZ', 日期 'YYYYMMDD'。"""
