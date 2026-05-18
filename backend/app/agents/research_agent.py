"""LangGraph 投研 Agent

变化点:
- 加 SystemMessage 注入投研助手人格 + 工具使用规则 + 合规边界
- 接入 session: 从 Redis 取历史 messages, 调用后回写
- 同时暴露 invoke 版 (一次性) 和 stream 版 (SSE)
"""
import operator
from typing import Annotated, AsyncIterator, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from backend.app.agents.prompts import SYSTEM_PROMPT
from backend.app.agents.session import load_history, save_history
from backend.app.llm.client import get_llm
from backend.app.tools import ALL_TOOLS


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]


def _build_graph():
    llm_with_tools = get_llm().bind_tools(ALL_TOOLS)

    def agent_node(state: AgentState) -> AgentState:
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(ALL_TOOLS))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")
    return graph.compile()


_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


async def _prepare_input(message: str, session_id: str) -> list[BaseMessage]:
    """组装入图的 messages: system + 历史 + 当前问题"""
    history = await load_history(session_id)
    return [SystemMessage(content=SYSTEM_PROMPT), *history, HumanMessage(content=message)]


def _extract_tool_calls(messages: list[BaseMessage]) -> list[dict]:
    """从消息流里提取所有 tool 调用记录, 用于返回给前端展示"""
    calls = []
    for m in messages:
        for tc in getattr(m, "tool_calls", []) or []:
            calls.append({"name": tc.get("name"), "args": tc.get("args")})
    return calls


# ──────────────────────────────────────────────────────
# 一次性调用 (普通 POST /chat)
# ──────────────────────────────────────────────────────
async def run_research_agent(message: str, session_id: str) -> dict:
    """运行 Agent, 返回 answer + tool_calls"""
    inputs = await _prepare_input(message, session_id)
    result = await _get_graph().ainvoke({"messages": inputs})

    last = result["messages"][-1]
    answer = last.content if isinstance(last.content, str) else str(last.content)

    # 持久化: 用户问题 + 最终 AI 回答 (中间的 tool messages 不存)
    new_history = [
        *(m for m in inputs if not isinstance(m, SystemMessage)),
        AIMessage(content=answer),
    ]
    await save_history(session_id, new_history)

    return {
        "answer": answer,
        "tool_calls": _extract_tool_calls(result["messages"]),
    }


# ──────────────────────────────────────────────────────
# 流式调用 (SSE /chat/stream)
# ──────────────────────────────────────────────────────
async def stream_research_agent(message: str, session_id: str) -> AsyncIterator[dict]:
    """流式运行 Agent, 逐步产出事件:
    - {"type": "tool_call", "name": "...", "args": {...}}
    - {"type": "tool_result", "name": "...", "content": "..."}
    - {"type": "token", "content": "..."}    # AI 文本片段
    - {"type": "done", "answer": "..."}      # 完成
    """
    inputs = await _prepare_input(message, session_id)
    graph = _get_graph()

    final_answer_parts: list[str] = []

    async for event in graph.astream_events(
        {"messages": inputs},
        version="v2",
    ):
        kind = event["event"]

        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            text = chunk.content if isinstance(chunk.content, str) else ""
            if text:
                final_answer_parts.append(text)
                yield {"type": "token", "content": text}

        elif kind == "on_tool_start":
            yield {
                "type": "tool_call",
                "name": event.get("name", ""),
                "args": event["data"].get("input", {}),
            }

        elif kind == "on_tool_end":
            output = event["data"].get("output")
            content = output.content if isinstance(output, ToolMessage) else str(output)
            yield {
                "type": "tool_result",
                "name": event.get("name", ""),
                "content": content[:500],  # 截断, 不刷屏
            }

    final_answer = "".join(final_answer_parts).strip()
    yield {"type": "done", "answer": final_answer}

    # 持久化
    new_history = [
        *(m for m in inputs if not isinstance(m, SystemMessage)),
        AIMessage(content=final_answer),
    ]
    await save_history(session_id, new_history)
