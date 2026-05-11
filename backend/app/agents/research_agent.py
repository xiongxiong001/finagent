"""LangGraph 投研 Agent"""
import operator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from backend.app.llm.client import get_llm
from backend.app.tools import ALL_TOOLS


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]


def _build_graph() -> StateGraph:
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


async def run_research_agent(message: str, session_id: str) -> dict:
    """运行投研 Agent，返回 answer 和 tool_calls 列表"""
    result = await _get_graph().ainvoke(
        {"messages": [HumanMessage(content=message)]}
    )
    last = result["messages"][-1]
    tool_calls = [
        {"name": tc["name"], "args": tc["args"]}
        for msg in result["messages"]
        for tc in getattr(msg, "tool_calls", [])
    ]
    return {"answer": last.content, "tool_calls": tool_calls}