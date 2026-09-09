"""把现有百万级 SQLite / IVF-PQ 索引接入 LangChain Retriever 协议。"""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field

from app.models import SourceDocument


class MedicalIndexRetriever(BaseRetriever):
    """复用稳定 rowid、原始来源权限和现有 Embedding 编码规则。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    channel: Literal["bm25", "faiss"]
    top_k: int
    sqlite_index: Any = None
    vector_index: Any = None
    memory_index: Any = None
    documents: list[SourceDocument] = Field(default_factory=list)

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        """独立召回一个通道并返回标准 Document，不复制整个索引到内存。

        Args:
            query: 当前已脱敏的医学查询。
            run_manager: LangChain 提供的 Retriever 回调管理器。

        Returns:
            含源文档、通道分数、来源权限的标准文档列表。
        """
        if self.channel == "bm25":
            if self.sqlite_index is not None:
                matches = self.sqlite_index.search(query, self.top_k)
            elif self.memory_index is not None:
                matches = [(self.documents[index], score)
                           for index, score in self.memory_index.search(query, self.top_k)]
            else:
                matches = []
        elif self.vector_index is not None and self.sqlite_index is not None:
            rows = self.vector_index.search(query, self.top_k)
            documents = self.sqlite_index.get_by_rowids([rowid for rowid, _ in rows])
            matches = [(documents[rowid], score) for rowid, score in rows if rowid in documents]
        else:
            matches = []
        return [
            Document(id=document.id, page_content=document.content, metadata={
                "source_document": document.model_dump(),
                "score": float(score), "channel": self.channel,
            })
            for document, score in matches
        ]


def restore_matches(documents: list[Document]) -> list[tuple[SourceDocument, float]]:
    """恢复领域文档和分数，使 RRF、人群过滤及引用继续使用原始元数据。

    Args:
        documents: Retriever 返回的 LangChain 文档。

    Returns:
        未改变顺序的源文档与分数元组。
    """
    return [(SourceDocument.model_validate(item.metadata["source_document"]),
             float(item.metadata["score"])) for item in documents]
