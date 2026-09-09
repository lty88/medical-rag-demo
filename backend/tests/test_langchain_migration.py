"""离线验证 LangChain 真实 SDK 请求、图分支与索引协议兼容性。"""

import json
import time
import unittest
from dataclasses import replace
from unittest.mock import MagicMock, patch

import httpx
from langchain.chat_models import init_chat_model

from app.config import Settings
from app.models import ResearchSearchResponse, SourceDocument
from app.services.document_graph import MedicalDocumentGraph
from app.services.document_interpreter import ExtractedMedicalDocument, MedicalDocumentInterpreter
from app.services.langchain_chat import complete_json, ModelCallError, parse_complete_json
from app.services.langchain_retrieval import MedicalIndexRetriever, restore_matches


class ChatTransportTests(unittest.TestCase):
    """使用模拟 HTTP 传输验证真实 LangChain 与 SDK 的序列化。"""

    def setUp(self) -> None:
        """准备固定响应与捕获请求列表，不访问真实模型。"""
        self.requests = []
        self.finish_reason = "stop"
        self.content = '{"title":"测试","summary":"说明","sections":[]}'
        self.status = 200
        self.options = dict(
            base_url="https://mock.example/v1/chat/completions",
            api_key="test-secret", model="mock-model",
            system_prompt="输出 JSON", user_content='含花括号 {"value":1}',
            timeout=3, max_tokens=2400, enable_thinking=False,
            request_id="local-check", stage="test",
        )
        self.http = httpx.Client(transport=httpx.MockTransport(self.handle))
        self.addCleanup(self.http.close)

    def handle(self, request: httpx.Request) -> httpx.Response:
        """捕获 SDK 请求并返回可配置响应。

        Args:
            request: 实际 SDK 序列化的 HTTP 请求。

        Returns:
            成功或权限失败的模拟模型响应。
        """
        self.requests.append(request)
        if self.status != 200:
            return httpx.Response(self.status, json={"error": {"message": "private report text"}})
        return httpx.Response(200, json={
            "id": "mock-id", "model": "mock-model", "object": "chat.completion",
            "created": 0,
            "choices": [{"index": 0, "finish_reason": self.finish_reason,
                         "message": {"role": "assistant", "content": self.content}}],
        })

    def factory(self, **kwargs):
        """给真实模型工厂注入本地模拟 HTTP 连接。

        Args:
            kwargs: 业务层传入模型、Token 和兼容参数。

        Returns:
            不访问网络的真实 ChatOpenAI 实例。
        """
        return init_chat_model(**kwargs, http_client=self.http)

    def call(self, **changes):
        """在模拟传输下调用共享入口。

        Args:
            changes: 覆盖本次调用选项。

        Returns:
            经过完整性解析的模型结果。
        """
        with patch("app.services.langchain_chat.init_chat_model", side_effect=self.factory):
            return complete_json(**(self.options | changes))

    def test_compatible_url_and_provider_options(self):
        """验证完整旧地址、思考开关与消息中的 JSON 不被提示词模板破坏。"""
        with self.assertLogs("uvicorn.error.medical_rag.langchain", level="INFO") as logs:
            result = self.call()
        payload = json.loads(self.requests[0].content)
        self.assertEqual(str(self.requests[0].url), "https://mock.example/v1/chat/completions")
        self.assertIs(payload["enable_thinking"], False)
        self.assertEqual(payload["messages"][1]["content"], self.options["user_content"])
        self.assertEqual(result["title"], "测试")
        self.assertNotIn("test-secret", "\n".join(logs.output))
        self.assertNotIn(self.options["user_content"], "\n".join(logs.output))

    def test_json_mode_and_image_content(self):
        """视觉块原样发送且 json_mode 使用服务端结构化输出。"""
        image = [{"type": "text", "text": "报告"},
                 {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}}]
        self.call(user_content=image, structured_method="json_mode")
        payload = json.loads(self.requests[0].content)
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["messages"][1]["content"], image)

    def test_truncation_is_never_treated_as_success(self):
        """即使正文看似完整，长度终止也不得输出可能缺失风险字段的报告。"""
        self.finish_reason = "length"
        with self.assertRaisesRegex(ModelCallError, "长度上限"):
            self.call()

    def test_http_error_does_not_expose_provider_body(self):
        """HTTP 错误保留状态且不传播服务商回显的报告正文。"""
        self.status = 403
        with self.assertRaisesRegex(ModelCallError, "HTTP 403") as error:
            self.call()
        self.assertNotIn("private report text", str(error.exception))
        self.assertEqual(len(self.requests), 1)

    def test_incomplete_outer_object_rejects_inner_object(self):
        """拒绝旧解析器可能错误采纳的截断报告内层对象。"""
        with self.assertRaises(ModelCallError):
            parse_complete_json('{"findings":[{"name":"局部结果"}], "summary":')
        self.assertEqual(parse_complete_json('说明 {"summary":"完整"} 结束')["summary"], "完整")


class RetrieverAndDocumentTests(unittest.TestCase):
    """验证迁移不会破坏 ID 映射、权限和报告证据传递。"""

    def test_faiss_rowid_roundtrip_preserves_permissions(self):
        """FAISS 仅查 rowid，再从 SQLite 获取带权限的源文档。"""
        source = SourceDocument(id="source-9", title="测试", content="原文",
                                source="fixture", source_type="medical_qa",
                                allow_treatment_generation=False)
        vector, sqlite = MagicMock(), MagicMock()
        vector.search.return_value = [(1234, .9)]
        sqlite.get_by_rowids.return_value = {1234: source}
        retriever = MedicalIndexRetriever(channel="faiss", top_k=4,
                                         sqlite_index=sqlite, vector_index=vector)
        matches = restore_matches(retriever.invoke("测试"))
        sqlite.get_by_rowids.assert_called_once_with([1234])
        self.assertEqual(matches[0][0].model_dump(), source.model_dump())
        self.assertEqual(matches[0][1], .9)

    def test_document_graph_passes_evidence_to_model(self):
        """报告图把独立检索结果真正传入生成步骤并保留响应结构。"""
        settings = replace(Settings(), llm_base_url="https://mock.example/v1",
                           llm_api_key="test-secret", llm_model="mock")
        service = MedicalDocumentInterpreter(settings)
        evidence = ResearchSearchResponse(request_id="evidence", query="检查", total=0,
                                          results=[], retrieval_mode="mock", duration_ms=0)
        search = MagicMock(return_value=evidence)
        graph = MedicalDocumentGraph(service, search)
        document = ExtractedMedicalDocument("report.txt", "other", "text", "检查报告测试文字")
        output = {"title": "解释", "summary": "资料不完整", "urgency": "insufficient",
                  "findings": [], "sections": [{"title": "说明", "content": "待医生确认"}]}
        with patch("app.services.document_interpreter.complete_json", return_value=output) as call:
            result = graph.run({"document": document, "symptoms": "", "focus": "",
                                "request_id": "report", "started_at": time.perf_counter()})
        self.assertEqual(result.request_id, "report")
        self.assertIn(document.text, call.call_args.kwargs["user_content"])
        self.assertEqual(search.call_count, 1)
