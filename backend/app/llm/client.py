"""DeepSeek LLM 客户端封装 (OpenAI 兼容协议)"""
from functools import lru_cache

from langchain_openai import ChatOpenAI

from backend.app.core.config import get_settings


@lru_cache
def get_llm() -> ChatOpenAI:
    """返回单例 LLM 实例; streaming=True 让 astream_events 能拿到 token 流"""
    settings = get_settings()
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout=settings.llm_timeout,
        streaming=True,
    )
