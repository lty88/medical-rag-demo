"""以 LangGraph 编排提取后的报告检索和解读，原始文件不进入图状态。"""

from collections.abc import Callable
from typing import Any, TypedDict

from langgraph.graph import START, END, StateGraph
from langsmith import tracing_context

from app.models import MedicalDocumentInterpretationResponse, ResearchSearchRequest, ResearchSearchResponse
from app.services.document_interpreter import ExtractedMedicalDocument, MedicalDocumentInterpreter


class DocumentState(TypedDict, total=False):
    """仅保留已提取文字与当前请求的结果，不包含原始图片字节。"""

    document: ExtractedMedicalDocument
    symptoms: str
    focus: str
    request_id: str
    started_at: float
    evidence: ResearchSearchResponse
    response: MedicalDocumentInterpretationResponse


class MedicalDocumentGraph:
    """复用统一 Retriever 和 LangChain 模型入口的报告工作流。"""

    def __init__(
        self,
        interpreter: MedicalDocumentInterpreter,
        search: Callable[[ResearchSearchRequest], ResearchSearchResponse],
    ) -> None:
        """编译报告解读图并注入检索与模型服务。

        Args:
            interpreter: 格式提取和结构化解读服务。
            search: 医疗混合检索入口。
        """
        self.interpreter = interpreter
        self.search = search
        builder = StateGraph(DocumentState)
        builder.add_node("retrieve", self._retrieve)
        builder.add_node("interpret", self._interpret)
        builder.add_edge(START, "retrieve")
        builder.add_edge("retrieve", "interpret")
        builder.add_edge("interpret", END)
        self.graph = builder.compile()

    def run(self, state: DocumentState) -> MedicalDocumentInterpretationResponse:
        """执行报告图并禁用云端跟踪；不创建持久化检查点。

        Args:
            state: 已完成文件校验和转录的请求数据。

        Returns:
            与现有上传接口兼容的报告解读结果。
        """
        with tracing_context(enabled=False):
            result = self.graph.invoke(state, config={"run_name": "medical-document"})
        return result["response"]

    def _retrieve(self, state: DocumentState) -> dict[str, Any]:
        """结合症状、报告开头与末尾结论触发本地混合检索。

        Args:
            state: 当前报告与可选症状背景。

        Returns:
            供模型引用的本地证据。
        """
        text = state["document"].text
        query = " ".join(filter(None, [state["symptoms"].strip()[:150],
                                       state["focus"].strip()[:100], text[:100], text[-150:]]))[:500]
        return {"evidence": self.search(ResearchSearchRequest(query=query, top_k=4))}

    def _interpret(self, state: DocumentState) -> dict[str, Any]:
        """把报告与最终证据交给共享 LangChain 入口并执行现有结构校验。

        Args:
            state: 包含报告、症状与已召回证据的图状态。

        Returns:
            最终报告解读响应。
        """
        return {"response": self.interpreter.interpret(
            state["document"], state["symptoms"], state["focus"], state["evidence"],
            state["request_id"], state["started_at"],
        )}
