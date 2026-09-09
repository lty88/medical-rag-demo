"""独立自由对话接口协议，不接收客户端伪造的历史或系统提示。"""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ChatSessionRequest(BaseModel):
    """随机会话凭据，仅放在请求正文中，不放入访问日志 URL。"""

    session_id: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class ChatMessageRequest(ChatSessionRequest):
    """当前用户消息以及用于网络重试去重的请求标识。"""

    message: str = Field(min_length=1, max_length=4000)
    request_id: UUID

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        """拒绝仅有空白的输入。

        Args:
            value: 用户本轮输入。

        Returns:
            去除首尾空白的非空消息。
        """
        if not value.strip():
            raise ValueError("请输入对话内容")
        return value.strip()


class ChatSessionResponse(BaseModel):
    """会话建立或清空后的内存策略。"""

    session_id: str
    model: str
    expires_in_seconds: int
    memory_limit_turns: int
    memory_max_characters: int


class ChatMessageResponse(BaseModel):
    """一次成功的直接模型回答，不携带 RAG 引用或安全校验结论。"""

    request_id: str
    reply: str
    model: str
    memory_turns: int
    expires_in_seconds: int
