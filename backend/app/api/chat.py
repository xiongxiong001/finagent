"""对话路由"""
import uuid
from fastapi import APIRouter

from backend.app.models.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])



@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """占位接口 - Day 3 接入 LangGraph Agent"""
    # TODO(Day 3): from backend.app.agents import run_research_agent
    #              result = await run_research_agent(req.message, session_id)
    session_id = req.session_id or str(uuid.uuid4())
    return ChatResponse(
        session_id=session_id,
        answer=f"[占位] 收到：{req.message}。Day 3 接入 Agent 后真正回答。",
        tool_calls=[],
    )