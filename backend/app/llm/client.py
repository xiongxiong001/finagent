"""DeepSeek LLM 客户端封装"""
from functools import lru_cache
from langchain_openai import ChatOpenAI
from backend.app.core.config import get_settings


@lru_cache
def get_llm() -> ChatOpenAI:
    """返回单例 DeepSeek LLM 实例"""
    settings = get_settings()
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.1,
        max_tokens=4096,
    )
