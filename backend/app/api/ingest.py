"""研报导入路由"""
from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.core.logger import logger
from backend.app.models.ingest import IngestResponse
from backend.app.rag.ingester import ingest_pdf

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/report", response_model=IngestResponse)
async def ingest_report(file: UploadFile = File(...)) -> IngestResponse:
    """上传研报 PDF, 解析 / 切块 / 向量化 / 写入 Qdrant"""
    filename = file.filename or "unknown.pdf"

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="目前仅支持 PDF 格式")

    content = await file.read()

    try:
        n_chunks = await ingest_pdf(content, filename)
    except RuntimeError as e:
        logger.error(f"ingest 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return IngestResponse(
        filename=filename,
        status="ok",
        message=f"导入成功, 共写入 {n_chunks} 个文本片段",
        chunks=n_chunks,
    )
