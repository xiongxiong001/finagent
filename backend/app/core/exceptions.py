"""自定义异常体系"""


class FinAgentError(Exception):
    """FinAgent 基础异常"""


class LLMError(FinAgentError):
    """LLM 调用异常"""


class RAGError(FinAgentError):
    """RAG 检索/导入异常"""


class ToolError(FinAgentError):
    """工具调用异常"""


class ConfigError(FinAgentError):
    """配置缺失或无效"""
