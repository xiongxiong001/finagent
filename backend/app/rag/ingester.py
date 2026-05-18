"""研报导入管道: PDF → chunks → embeddings → Qdrant

设计要点:
- 用 pdfplumber 解析, 对研报里的表格/段落兼容性好
- 用 RecursiveCharacterTextSplitter 切块, 中文场景 chunk_size=800/overlap=100 是常见甜点
- Qdrant collection 不存在时自动创建, 维度从 settings.embedding_dim 读取
- 用 uuid 作为 point id, 多次 ingest 同一文件不会主键冲突
- 文件级元数据写入 payload, 检索时能溯源
"""
import io
import uuid
from datetime import datetime

import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from backend.app.core.config import get_settings
from backend.app.core.logger import logger
from backend.app.rag.embedder import get_embeddings

COLLECTION_NAME = "research_reports"


def _extract_text_from_pdf(content: bytes) -> str:
    """从 PDF bytes 提取所有文本; 失败的页跳过"""
    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for i, page in enumerate(pdf.pages):
            try:
                text = page.extract_text() or ""
                if text.strip():
                    parts.append(text)
            except Exception as e:
                logger.warning(f"PDF 第 {i + 1} 页解析失败,跳过: {e}")
    return "\n\n".join(parts)


def _split_text(text: str) -> list[str]:
    """中文友好的分块"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", "。", "!", "?", ";", ",", " ", ""],
    )
    return [c.strip() for c in splitter.split_text(text) if c.strip()]


def _ensure_collection(client: QdrantClient, dim: int) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        logger.info(f"创建 Qdrant collection: {COLLECTION_NAME} (dim={dim})")


def _upsert_chunks(
    client: QdrantClient,
    chunks: list[str],
    vectors: list[list[float]],
    source: str,
) -> None:
    ingested_at = datetime.now().isoformat()
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vec,
            payload={
                "text": chunk,
                "source": source,
                "ingested_at": ingested_at,
                "chunk_index": i,
            },
        )
        for i, (chunk, vec) in enumerate(zip(chunks, vectors))
    ]
    client.upsert(collection_name=COLLECTION_NAME, points=points)


async def ingest_pdf(content: bytes, filename: str) -> int:
    """解析 PDF, 切块, 向量化后写入 Qdrant, 返回写入的 chunk 数。

    任一步失败会抛 RuntimeError, 由路由层捕获并返回 500。
    """
    if not content:
        raise RuntimeError("文件内容为空")

    logger.info(f"[ingest] 开始处理 {filename} ({len(content)} bytes)")

    # 1. 解析
    text = _extract_text_from_pdf(content)
    if not text.strip():
        raise RuntimeError(f"{filename} 未提取到任何文本(可能是扫描版 PDF, 需要 OCR)")
    logger.info(f"[ingest] 提取文本 {len(text)} 字符")

    # 2. 切块
    chunks = _split_text(text)
    if not chunks:
        raise RuntimeError("切块结果为空")
    logger.info(f"[ingest] 切分为 {len(chunks)} 个 chunks")

    # 3. 向量化 (langchain-openai 的 embed_documents 是同步, 但内部走 httpx, 不阻塞 GIL 太久)
    settings = get_settings()
    vectors = get_embeddings().embed_documents(chunks)
    logger.info(f"[ingest] 向量化完成, 维度 {len(vectors[0]) if vectors else 0}")

    # 4. 写入 Qdrant
    client = QdrantClient(url=settings.qdrant_url)
    _ensure_collection(client, dim=len(vectors[0]))
    _upsert_chunks(client, chunks, vectors, source=filename)

    logger.info(f"[ingest] {filename} 完成: {len(chunks)} chunks 已写入")
    return len(chunks)
