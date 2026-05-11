"""研报导入路由"""
from fastapi import APIRouter, UploadFile, File

from backend.app.models.ingest import IngestResponse

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/report", response_model=IngestResponse)
async def ingest_report(file: UploadFile = File(...)) -> IngestResponse:
    """占位接口 - Day 4 接入 PDF 解析 + 向量化"""
    # TODO(Day 4): content = await file.read()
    #              chunks = await ingest_pdf(content, file.filename)
    return IngestResponse(
        filename=file.filename or "unknown",
        status="pending",
        message="Day 4 接入真正的 RAG 导入能力",
        chunks=0,
    )