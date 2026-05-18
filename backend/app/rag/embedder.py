"""文本向量化

默认使用硅基流动的 BGE-M3 (OpenAI 兼容协议, 国内可访问, 中文召回好)。
想换真 OpenAI / 阿里百炼 / 火山引擎: 改 .env 的 EMBEDDING_* 三项即可。
"""
from functools import lru_cache

from langchain_openai import OpenAIEmbeddings

from backend.app.core.config import get_settings


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    """返回单例 Embeddings 实例"""
    settings = get_settings()
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.embedding_api_key,
        base_url=settings.embedding_base_url,
        # 一些兼容服务对 dimensions 字段不支持, 不显式传, 让服务端用默认值
        check_embedding_ctx_length=False,
    )
