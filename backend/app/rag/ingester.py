"""研报导入管道：PDF → chunks → embeddings → Qdrant"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from backend.app.rag.embedder import get_embeddings
from backend.app.core.config import get_settings
from backend.app.core.logger import logger

COLLECTION_NAME = "research_reports"
VECTOR_DIM = 1536  # text-embedding-3-small 维度


async def ingest_pdf(content: bytes, filename: str) -> int:
    """解析 PDF，切块，向量化后写入 Qdrant，返回写入的 chunk 数量。

    TODO(Day 4): 完整实现
      1. PDF 解析：pdfplumber / PyMuPDF
      2. 文本分块：RecursiveCharacterTextSplitter
      3. 向量化：get_embeddings().embed_documents(chunks)
      4. 写入 Qdrant：_upsert_chunks(chunks, vectors, filename)
    """
    logger.warning(f"ingest_pdf 尚未实现，文件 {filename} 已跳过")
    return 0


def _ensure_collection(client: QdrantClient) -> None:
    """若集合不存在则创建"""
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )


def _upsert_chunks(
    client: QdrantClient,
    chunks: list[str],
    vectors: list[list[float]],
    source: str,
    start_id: int = 0,
) -> None:
    points = [
        PointStruct(
            id=start_id + i,
            vector=vec,
            payload={"text": chunk, "source": source},
        )
        for i, (chunk, vec) in enumerate(zip(chunks, vectors))
    ]
    client.upsert(collection_name=COLLECTION_NAME, points=points)
