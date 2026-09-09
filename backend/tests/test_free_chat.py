"""自由对话的离线局部校验，不加载医疗模型或请求真实 LLM。"""

import unittest
from dataclasses import replace
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from app.chat_models import ChatMessageRequest
from app.config import Settings
from app.services.free_chat import FreeChatService
from app.services.langchain_chat import ModelCallError, complete_text


class FreeChatTests(unittest.TestCase):
    """验证 LangChain 真正注入历史，并检查记忆边界和接口契约。"""

    def setUp(self) -> None:
        """建立独立内存服务和假模型记录器，不触发网络或 RAG。"""
        self.service = FreeChatService(replace(
            Settings(), llm_base_url="https://mock.invalid/v1", llm_api_key="mock-key",
            llm_model="mock-chat",
        ))
        self.seen = []
        self.model = patch("app.services.free_chat.complete_text", side_effect=self.answer)
        self.model.start()
        self.addCleanup(self.model.stop)

    def answer(self, messages, **options):
        """记录实际传给模型的消息并返回固定文本。

        Args:
            messages: LangChain 提示词组装后的消息列表。
            options: 服务端模型参数。

        Returns:
            用于检验历史写入的助手消息。
        """
        self.seen.append(list(messages))
        return AIMessage(content="这是测试回答")

    def request(self, session_id, text="你好", request_id=None):
        """构造合法的独立会话请求。

        Args:
            session_id: 服务端会话凭据。
            text: 当前用户输入。
            request_id: 可复用的重试标识。

        Returns:
            已经通过 Pydantic 验证的请求。
        """
        return ChatMessageRequest(session_id=session_id, message=text, request_id=request_id or uuid4())

    def test_history_and_session_isolation(self):
        """第二轮包含上一轮完整问答，另一会话不会看见这些内容。"""
        first = self.service.create_session().session_id
        second = self.service.create_session().session_id
        self.service.send(self.request(first, "我正在学习 Python"))
        result = self.service.send(self.request(first, "我刚才在学什么？"))
        self.assertEqual(result.memory_turns, 2)
        self.assertEqual([item.type for item in self.seen[-1]], ["system", "human", "ai", "human"])
        self.assertIn("Python", self.seen[-1][1].content)
        self.service.send(self.request(second))
        self.assertEqual([item.type for item in self.seen[-1]], ["system", "human"])

    def test_failure_does_not_commit_or_trim_history(self):
        """模型失败不会留下孤立用户消息，也不会提前裁掉原始历史。"""
        key = self.service.create_session().session_id
        self.service.send(self.request(key))
        old_messages = self.service._history(self.service.sessions[key], key)
        with patch("app.services.free_chat.complete_text", side_effect=ModelCallError("超时", 504)):
            with self.assertRaises(ModelCallError):
                self.service.send(self.request(key, "后续问题"))
        self.assertEqual(self.service._history(self.service.sessions[key], key), old_messages)
        self.assertFalse(self.service.sessions[key].lock.locked())

    def test_retry_is_idempotent_and_clear_removes_memory(self):
        """最近一次重试不重复扣费或追加历史，清空会真实删除记忆和重试缓存。"""
        key = self.service.create_session().session_id
        request = self.request(key)
        self.assertEqual(self.service.send(request), self.service.send(request))
        self.assertEqual(len(self.seen), 1)
        with self.assertRaises(ModelCallError):
            self.service.send(self.request(key, "不同消息", request.request_id))
        self.service.clear(key)
        self.assertEqual(self.service._history(self.service.sessions[key], key), [])
        self.service.send(request)
        self.assertEqual(len(self.seen[-1]), 2)

    def test_bounded_history_preserves_complete_pairs(self):
        """仅保留最近完整问答，并限制历史和当前输入的总字符数。"""
        self.service.max_turns = 2
        self.service.max_characters = 36
        key = self.service.create_session().session_id
        for index in range(5):
            self.service.send(self.request(key, f"第{index}次对话"))
        history = self.service._history(self.service.sessions[key], key)
        self.assertLessEqual(len(history), 4)
        self.assertEqual([item.type for item in history], ["human", "ai"] * (len(history) // 2))
        self.assertLessEqual(sum(len(item.content) for item in history), 36)
        self.assertLessEqual(sum(len(item.content) for item in self.seen[-1][1:]), 36)

    def test_expiry_capacity_and_busy_session(self):
        """过期会话不可续聊、容量受限且并发清空被拒绝。"""
        self.service.max_sessions = 1
        key = self.service.create_session().session_id
        with self.assertRaises(ModelCallError) as capacity:
            self.service.create_session()
        self.assertEqual(capacity.exception.status_code, 503)
        session = self.service.acquire(key)
        try:
            with self.assertRaises(ModelCallError) as busy:
                self.service.clear(key)
            self.assertEqual(busy.exception.status_code, 409)
        finally:
            session.lock.release()
        session.touched -= self.service.ttl_seconds + 1
        with self.assertRaises(ModelCallError) as expired:
            self.service.send(self.request(key))
        self.assertEqual(expired.exception.status_code, 410)
        self.assertNotIn(key, self.service.sessions)

    def test_chat_routes_without_medical_pipeline(self):
        """单独挂载自由对话路由，验证创建、发送、清空、空白校验和过期状态。"""
        from app import chat_routes

        app = FastAPI()
        app.include_router(chat_routes.router)
        with patch.object(chat_routes, "free_chat", self.service), TestClient(app) as client:
            created = client.post("/api/chat/sessions", json={})
            self.assertEqual(created.status_code, 200)
            key = created.json()["session_id"]
            payload = self.request(key).model_dump(mode="json")
            self.assertEqual(client.post("/api/chat/messages", json=payload).json()["reply"], "这是测试回答")
            self.assertEqual(client.post("/api/chat/clear", json={"session_id": key}).status_code, 200)
            self.assertEqual(client.post("/api/chat/messages", json=payload | {"message": "  "}).status_code, 422)
            self.service.close()
            self.assertEqual(client.post("/api/chat/messages", json=payload).status_code, 410)


class DirectModelTests(unittest.TestCase):
    """检验文本模型出口，不允许不完整或空回答进入记忆。"""

    def test_complete_text_validation(self):
        """对文本、块状文本、空回答与截断回答做局部出口校验。"""
        cases = [
            (AIMessage(content="正常回答"), "正常回答"),
            (AIMessage(content=[{"type": "text", "text": "分块正文"}]), "分块正文"),
            (AIMessage(content=""), None),
            (AIMessage(content="未完成", response_metadata={"finish_reason": "length"}), None),
            (AIMessage(content="拒绝", response_metadata={"finish_reason": "content_filter"}), None),
        ]
        for message, expected in cases:
            with patch("app.services.langchain_chat.create_chat_model") as factory:
                factory.return_value.invoke.return_value = message
                if expected is None:
                    with self.assertRaises(ModelCallError):
                        complete_text([HumanMessage(content="问题")])
                else:
                    self.assertEqual(complete_text([HumanMessage(content="问题")]).content, expected)


if __name__ == "__main__":
    unittest.main()
