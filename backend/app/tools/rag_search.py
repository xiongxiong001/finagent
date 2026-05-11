"""工具 5/5：研报知识库 RAG 检索"""
from langchain_core.tools import tool
from backend.app.rag.retriever import retrieve
from backend.app.core.logger import logger


@tool
def search_research_reports(query: str, top_k: int = 5) -> str:
    """在已导入的研报知识库中检索与 query 最相关的内容片段。"""
    try:
        docs = retrieve(query=query, top_k=top_k)
        if not docs:
            return "知识库中未找到相关研报内容，请先通过 /ingest/report 导入研报。"
        parts = [
            f"[{i}] 来源: {doc.metadata.get('source', '未知')}\n{doc.page_content[:400]}"
            for i, doc in enumerate(docs, 1)
        ]
        return "\n\n".join(parts)
    except Exception as e:
        logger.error(f"search_research_reports 失败: {e}")
        return f"检索失败: {e}"