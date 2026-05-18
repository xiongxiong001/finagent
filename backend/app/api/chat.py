"""对话路由"""
import json
import uuid

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from backend.app.agents.research_agent import run_research_agent, stream_research_agent
from backend.app.core.logger import logger
from backend.app.models.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """一次性对话: 返回完整答案 + 工具调用记录"""
    session_id = req.session_id or str(uuid.uuid4())
    logger.info(f"[chat] session={session_id} msg={req.message[:60]}")
    result = await run_research_agent(req.message, session_id)
    return ChatResponse(
        session_id=session_id,
        answer=result["answer"],
        tool_calls=result["tool_calls"],
    )


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    """流式对话: SSE, 前端能逐步看到工具调用和 AI 文本

    事件类型:
      - tool_call:   Agent 正在调用工具
      - tool_result: 工具返回结果
      - token:       AI 输出文本片段
      - done:        本轮完成
    """
    session_id = req.session_id or str(uuid.uuid4())
    logger.info(f"[chat/stream] session={session_id} msg={req.message[:60]}")

    async def event_generator():
        # 第一个事件: 告诉客户端 session_id (前端要记下来下一轮带上)
        yield {"event": "session", "data": json.dumps({"session_id": session_id})}

        try:
            async for ev in stream_research_agent(req.message, session_id):
                yield {
                    "event": ev["type"],
                    "data": json.dumps(ev, ensure_ascii=False),
                }
        except Exception as e:
            logger.error(f"stream 异常: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)}, ensure_ascii=False),
            }

    return EventSourceResponse(event_generator())
