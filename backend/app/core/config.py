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

    # 应用
    app_name: str = "FinAgent"
    app_version: str = "0.1.0"
    debug: bool = Field(default=True, description="开发模式")

    # LLM
    deepseek_api_key: str = Field(default="", description="DeepSeek API Key")
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    # 数据源
    tushare_token: str = Field(default="", description="Tushare Pro Token")

    # LLM 高级配置
    llm_provider: str = Field(default="deepseek", description="LLM 提供商: deepseek | openai")
    llm_model: str = Field(default="deepseek-chat", description="默认模型名")
    llm_timeout: int = Field(default=60, description="请求超时（秒）")
    llm_max_retries: int = Field(default=3, description="网络错误最大重试次数")

    # OpenAI 兼容（llm_provider=openai 时生效）
    openai_api_key: str = Field(default="", description="OpenAI API Key")
    openai_base_url: str = Field(default="https://api.openai.com/v1", description="OpenAI-compatible base URL")

    # 基础设施
    database_url: str = "postgresql+asyncpg://finagent:finagent_dev_password@localhost:5432/finagent"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"


@lru_cache
def get_settings() -> Settings:
    """单例配置"""
    return Settings()