"""统一配置管理 - 所有环境变量从这里读"""
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── 应用 ────────────────────────────────────────────
    app_name: str = "FinAgent"
    app_version: str = "0.1.0"
    debug: bool = Field(default=True, description="开发模式")

    # ── LLM (DeepSeek, OpenAI 兼容) ─────────────────────
    deepseek_api_key: str = Field(default="", description="DeepSeek API Key")
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = Field(default="deepseek-chat", description="LLM 模型名")
    llm_temperature: float = Field(default=0.1)
    llm_max_tokens: int = Field(default=4096)
    llm_timeout: int = Field(default=60, description="请求超时(秒)")

    # ── Embedding (硅基流动 BGE-M3, OpenAI 兼容) ─────────
    # 硅基流动: https://siliconflow.cn 免费送 2000 万 tokens
    # 想换阿里百炼 / 火山引擎 / 真 OpenAI 改下面 3 项即可
    embedding_api_key: str = Field(default="", description="Embedding API Key")
    embedding_base_url: str = Field(
        default="https://api.siliconflow.cn/v1",
        description="Embedding API base URL",
    )
    embedding_model: str = Field(
        default="BAAI/bge-m3",
        description="Embedding 模型名",
    )
    embedding_dim: int = Field(default=1024, description="BGE-M3 输出 1024 维")

    # ── 数据源 ──────────────────────────────────────────
    data_source: str = Field(default="tushare", description="行情数据源: tushare | akshare")
    tushare_token: str = Field(default="", description="Tushare Pro Token")

    # ── 缓存 TTL (秒) ───────────────────────────────────
    cache_ttl_stock_basic: int = 86400      # 股票基本信息 1 天
    cache_ttl_stock_price: int = 300        # 股价 5 分钟 (盘中也够用)
    cache_ttl_financial: int = 86400        # 财务指标 1 天
    cache_ttl_news: int = 300               # 新闻 5 分钟
    cache_ttl_name_map: int = 86400         # 名称->代码映射 1 天

    # ── 基础设施 ────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://finagent:finagent_dev_password@localhost:5432/finagent"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    # ── 会话 ────────────────────────────────────────────
    session_ttl: int = Field(default=3600, description="对话历史保留时长(秒)")
    session_max_messages: int = Field(default=20, description="单会话最多保留多少轮消息")


@lru_cache
def get_settings() -> Settings:
    """单例配置"""
    return Settings()
