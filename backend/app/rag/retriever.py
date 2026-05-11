"""Qdrant 向量检索"""
from qdrant_client import QdrantClient
from langchain_core.documents import Document
from backend.app.rag.embedder import get_embeddings
from backend.app.core.config import get_settings

COLLECTION_NAME = "research_reports"


def retrieve(query: str, top_k: int = 5) -> list[Document]:
    """从 Qdrant 检索最相关的研报片段"""
    settings = get_settings()
    query_vector = get_embeddings().embed_query(query)

    client = QdrantClient(url=settings.qdrant_url)
    hits = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k,
    )

    return [
        Document(
            page_content=hit.payload.get("text", "") if hit.payload else "",
            metadata={
                "source": hit.payload.get("source", "") if hit.payload else "",
                "score": hit.score,
            },
        )
        for hit in hits
    ]
