"""自由对话路由，与问诊和报告检索链路隔离。"""

import asyncio

from fastapi import APIRouter, HTTPException

from app.chat_models import ChatMessageRequest, ChatMessageResponse, ChatSessionRequest, ChatSessionResponse
from app.config import settings
from app.services.free_chat import FreeChatService
from app.services.langchain_chat import ModelCallError

router = APIRouter(prefix="/api/chat", tags=["自由对话"])
free_chat = FreeChatService(settings)


async def cleanup_chat_sessions() -> None:
    """每分钟清理已闲置过期的短期记忆，应用退出时由生命周期取消。"""
    while True:
        await asyncio.sleep(60)
        free_chat.cleanup()


@router.post("/sessions", response_model=ChatSessionResponse)
def create_chat_session() -> ChatSessionResponse:
    """创建不关联其他用户或问诊数据的独立随机会话。

    Returns:
        会话凭据、模型名称及短期记忆限制。
    """
    try:
        return free_chat.create_session()
    except ModelCallError as error:
        raise HTTPException(error.status_code, str(error)) from error


@router.post("/messages", response_model=ChatMessageResponse)
def send_chat_message(request: ChatMessageRequest) -> ChatMessageResponse:
    """在线程池中直接调用 LLM，不阻塞异步路由，也不经过 RAG。

    Args:
        request: 会话凭据、用户本轮输入和重试标识。

    Returns:
        模型回答、模型名称和保留的记忆轮数。
    """
    try:
        return free_chat.send(request)
    except ModelCallError as error:
        raise HTTPException(error.status_code, str(error)) from error


@router.post("/clear", response_model=ChatSessionResponse)
def clear_chat_session(request: ChatSessionRequest) -> ChatSessionResponse:
    """清空指定会话的服务端短期记忆，而非仅清除前端聊天列表。

    Args:
        request: 要清空的会话凭据。

    Returns:
        清空后可以继续使用的会话说明。
    """
    try:
        return free_chat.clear(request.session_id)
    except ModelCallError as error:
        raise HTTPException(error.status_code, str(error)) from error
