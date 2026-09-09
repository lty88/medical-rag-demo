"""不依赖 RAG 的 LangChain 对话和有界进程内短期记忆。"""

from __future__ import annotations

import secrets
import time
from _thread import LockType
from dataclasses import dataclass, field
from threading import Lock, RLock
from typing import TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langsmith import tracing_context

from app.chat_models import ChatMessageRequest, ChatMessageResponse, ChatSessionResponse
from app.config import Settings
from app.services.langchain_chat import ModelCallError, complete_text

SYSTEM_PROMPT = (
    "你是一个中文通用对话助手，请结合本次会话上下文准确、清晰地回答。"
    "你没有检索知识库、联网或访问用户病历，不得声称已检索、核实引用或看过未提供的资料。"
    "不确定时说明不确定。涉及医疗内容时仅作一般信息解释，不作个体诊断、处方或剂量调整；"
    "如用户描述可能危及生命的症状，优先提示立即寻求当地急救帮助。"
    "若用户引用已不在当前上下文的内容，请其补充，不要编造记忆。"
)


class ChatState(TypedDict):
    """检查点内的有限完整问答和本轮回答；消息列表整体替换，不无限累加。"""

    messages: list[BaseMessage]
    reply: str


@dataclass
class ChatSession:
    """按不可预测凭据隔离的内存检查点、串行锁和最近一次幂等结果。"""

    checkpointer: InMemorySaver = field(default_factory=InMemorySaver)
    lock: LockType = field(default_factory=Lock)
    touched: float = field(default_factory=time.monotonic)
    last_request: str = ""
    last_input: str = ""
    last_response: ChatMessageResponse | None = None


class FreeChatService:
    """仅保存最近完整问答，不持久化、不跨会话检索、不启用追踪上传。"""

    ttl_seconds = 1800
    max_sessions = 128
    max_turns = 12
    max_characters = 24000

    def __init__(self, settings: Settings) -> None:
        """初始化会话仓库；不会加载 Embedding 或建立模型网络连接。

        Args:
            settings: 已有的服务端 LLM 配置。
        """
        self.settings = settings
        self.sessions: dict[str, ChatSession] = {}
        self.lock = RLock()
        self.workflow = StateGraph(ChatState)
        self.workflow.add_node("respond", self._respond)
        self.workflow.add_edge(START, "respond")
        self.workflow.add_edge("respond", END)

    def cleanup(self) -> None:
        """清除超过闲置期限且没有进行中请求的会话，不输出会话正文。"""
        with self.lock:
            now = time.monotonic()
            for key, session in list(self.sessions.items()):
                if now - session.touched >= self.ttl_seconds and not session.lock.locked():
                    del self.sessions[key]

    def close(self) -> None:
        """应用关闭时丢弃本进程所有会话与幂等缓存。"""
        with self.lock:
            self.sessions.clear()

    def describe(self, session_id: str) -> ChatSessionResponse:
        """生成可供前端明确展示的模型与短期记忆策略。

        Args:
            session_id: 服务端生成的会话凭据。

        Returns:
            不含密钥和模型服务地址的会话说明。
        """
        return ChatSessionResponse(
            session_id=session_id, model=self.settings.llm_model or "未配置",
            expires_in_seconds=self.ttl_seconds, memory_limit_turns=self.max_turns,
            memory_max_characters=self.max_characters,
        )

    def create_session(self) -> ChatSessionResponse:
        """分配新会话凭据；达到容量限制时拒绝创建，避免挤掉其他用户的历史。

        Returns:
            新会话凭据与记忆策略。
        """
        if not all((self.settings.llm_base_url, self.settings.llm_api_key, self.settings.llm_model)):
            raise ModelCallError("请先配置 LLM_BASE_URL、LLM_API_KEY 和 LLM_MODEL", 503)
        with self.lock:
            self.cleanup()
            if len(self.sessions) >= self.max_sessions:
                raise ModelCallError("当前会话容量已满，请稍后再试", 503)
            session_id = secrets.token_urlsafe(32)
            self.sessions[session_id] = ChatSession()
        return self.describe(session_id)

    def acquire(self, session_id: str) -> ChatSession:
        """验证会话并获取独占锁，避免同会话并发回答或清空时历史乱序。

        Args:
            session_id: 客户端持有的随机会话凭据。

        Returns:
            已加锁的会话，调用方必须最终释放锁。
        """
        with self.lock:
            self.cleanup()
            session = self.sessions.get(session_id)
            if session is None:
                raise ModelCallError("会话已过期或服务已重启，请开始新对话", 410)
            if not session.lock.acquire(blocking=False):
                raise ModelCallError("当前会话正在回答，请等待完成", 409)
            session.touched = time.monotonic()
            return session

    def clear(self, session_id: str) -> ChatSessionResponse:
        """立即清空指定会话的历史和重试缓存。

        Args:
            session_id: 需清除历史的会话凭据。

        Returns:
            已清空会话的记忆策略。
        """
        session = self.acquire(session_id)
        try:
            session.checkpointer.delete_thread(session_id)
            session.last_request = session.last_input = ""
            session.last_response = None
            return self.describe(session_id)
        finally:
            session.lock.release()

    def _invoke_model(self, prompt: ChatPromptValue) -> AIMessage:
        """发送有界历史和本轮输入到直接模型，不调用任何检索服务。

        Args:
            prompt: LangChain 拼装的系统提示、历史及当前消息。

        Returns:
            已校验的纯文本助手消息。
        """
        config = self.settings
        return complete_text(
            prompt.to_messages(), base_url=config.llm_base_url, api_key=config.llm_api_key,
            model=config.llm_model, timeout=config.llm_timeout_seconds,
            max_tokens=config.llm_max_output_tokens, enable_thinking=config.llm_enable_thinking,
        )

    def _history(self, session: ChatSession, session_id: str) -> list[BaseMessage]:
        """读取该会话最近一次成功提交的检查点消息副本。

        Args:
            session: 已持有独占锁的会话。
            session_id: 对应的 LangGraph thread_id。

        Returns:
            最新完整历史消息，尚未开始对话时为空列表。
        """
        checkpoint = session.checkpointer.get({"configurable": {"thread_id": session_id}})
        return list(checkpoint["channel_values"].get("messages", [])) if checkpoint else []

    def _trim(self, messages: list[BaseMessage], reserved: int = 0) -> None:
        """按完整问答对删除最早历史，限制轮数和正文字符数。

        Args:
            messages: 本次请求的历史副本或成功后待保存的记忆。
            reserved: 为当前用户输入预留的字符数。
        """
        while messages and (
            len(messages) > self.max_turns * 2
            or sum(len(str(message.content)) for message in messages) + reserved > self.max_characters
        ):
            del messages[:2]

    def _respond(self, state: ChatState) -> ChatState:
        """LangGraph 单节点直接生成回答，并将完整问答裁剪后写入局部检查点。

        Args:
            state: 有界历史和本轮用户输入。

        Returns:
            完整回答及允许保留的消息状态。
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT), MessagesPlaceholder("messages"),
        ])
        answer = self._invoke_model(prompt.invoke({"messages": state["messages"]}))
        messages = [*state["messages"], answer]
        self._trim(messages)
        return {"messages": messages, "reply": str(answer.content)}

    def send(self, request: ChatMessageRequest) -> ChatMessageResponse:
        """执行带短期记忆的 LangChain 会话，只有完整成功后才提交历史。

        Args:
            request: 会话凭据、本轮文本和网络重试标识。

        Returns:
            纯文本回答及当前仍保留的记忆轮数。
        """
        session = self.acquire(request.session_id)
        try:
            request_id = str(request.request_id)
            if session.last_request == request_id:
                if session.last_input != request.message:
                    raise ModelCallError("重复请求标识不能用于不同消息", 409)
                if session.last_response is not None:
                    return session.last_response
            history = self._history(session, request.session_id)
            self._trim(history, reserved=len(request.message))
            # 请求局部检查点只有成功才替换会话检查点，失败的输入或半截回答不会提交。
            # 每次替换也释放旧检查点版本，防止短期记忆虽裁剪但历史快照无限增长。
            checkpointer = InMemorySaver()
            with tracing_context(enabled=False):
                graph = self.workflow.compile(checkpointer=checkpointer)
                result = graph.invoke(
                    {"messages": [*history, HumanMessage(content=request.message)], "reply": ""},
                    config={"configurable": {"thread_id": request.session_id}},
                )
            response = ChatMessageResponse(
                request_id=request_id, reply=result["reply"], model=self.settings.llm_model or "",
                memory_turns=len(result["messages"]) // 2, expires_in_seconds=self.ttl_seconds,
            )
            session.checkpointer = checkpointer
            session.last_request, session.last_input = request_id, request.message
            session.last_response = response
            return response
        finally:
            session.touched = time.monotonic()
            session.lock.release()
