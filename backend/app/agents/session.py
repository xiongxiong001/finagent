"""会话历史: 存 Redis, 跨进程 / 跨重启复用

序列化策略:
- LangChain 的 messages 已有 to/from dict 方法, 这里直接 JSON 化
- 只存 HumanMessage / AIMessage 的对话主线, ToolMessage 不入持久化
  (Agent 调用工具是这一轮的中间过程, 下一轮没必要重放)
"""
import json
from typing import Iterable

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from backend.app.core.config import get_settings
from backend.app.core.logger import logger
from backend.app.core.redis_client import get_redis


def _key(session_id: str) -> str:
    return f"session:{session_id}:messages"


def _message_to_dict(m: BaseMessage) -> dict:
    if isinstance(m, HumanMessage):
        return {"role": "human", "content": m.content}
    if isinstance(m, AIMessage):
        # 只保留文本, tool_calls 不入持久化
        return {"role": "ai", "content": m.content}
    return {"role": m.type, "content": m.content}


def _dict_to_message(d: dict) -> BaseMessage:
    role = d.get("role", "")
    content = d.get("content", "")
    if role == "human":
        return HumanMessage(content=content)
    return AIMessage(content=content)


async def load_history(session_id: str) -> list[BaseMessage]:
    """加载历史对话; 不存在返回空列表"""
    try:
        raw = await get_redis().get(_key(session_id))
        if not raw:
            return []
        items = json.loads(raw)
        return [_dict_to_message(d) for d in items]
    except Exception as e:
        logger.warning(f"加载会话 {session_id} 失败: {e}")
        return []


async def save_history(session_id: str, messages: Iterable[BaseMessage]) -> None:
    """保存对话; 只保留最近 N 轮, 防止 context 越来越长"""
    settings = get_settings()
    keep_only = [m for m in messages if isinstance(m, (HumanMessage, AIMessage))]
    # 保留最近 session_max_messages 条
    keep_only = keep_only[-settings.session_max_messages:]
    payload = json.dumps([_message_to_dict(m) for m in keep_only], ensure_ascii=False)
    try:
        await get_redis().setex(_key(session_id), settings.session_ttl, payload)
    except Exception as e:
        logger.warning(f"保存会话 {session_id} 失败: {e}")
