"""文本向量化"""
from functools import lru_cache
from langchain_openai import OpenAIEmbeddings
from backend.app.core.config import get_settings


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    """返回单例 Embeddings 实例，复用 DeepSeek API Key"""
    settings = get_settings()
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )
