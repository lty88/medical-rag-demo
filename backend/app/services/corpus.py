"""加载内置示例与已拉取的 Huatuo 分片。"""

from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

from app.models import KnowledgeStats, SourceDocument


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """逐行读取普通或 gzip 压缩的 JSONL 文件。

    Args:
        path: JSONL 或 JSONL.GZ 文件路径。

    Yields:
        每行解析得到的字典。
    """

    source_file = (
        gzip.open(path, "rt", encoding="utf-8")
        if path.suffix == ".gz"
        else path.open("r", encoding="utf-8")
    )
    with source_file:
        for line in source_file:
            if line.strip():
                yield json.loads(line)


def load_documents(
    sample_path: Path, raw_dir: Path, max_documents: int
) -> tuple[list[SourceDocument], bool]:
    """先加载可信演示条目，再按上限加载已下载问答。

    Args:
        sample_path: 内置演示知识文件。
        raw_dir: Huatuo gzip 分片目录。
        max_documents: 允许驻留内存的最大文档数。

    Returns:
        文档列表以及是否因上限停止加载的标记。
    """

    documents: list[SourceDocument] = []
    capped = False
    paths = [sample_path] if sample_path.exists() else []
    paths.extend(sorted(raw_dir.glob("*.jsonl.gz")))

    for path in paths:
        for row in iter_jsonl(path):
            if len(documents) >= max_documents:
                capped = True
                break
            try:
                documents.append(SourceDocument.model_validate(row))
            except ValueError:
                continue
        if capped:
            break
    return documents, capped


def build_stats(
    documents: list[SourceDocument],
    vector_mode: str,
    reranker_mode: str,
    capped: bool,
    embedding_model: str | None,
    reranker_model: str | None,
) -> KnowledgeStats:
    """统计知识库来源、可信等级和当前检索实现。

    Args:
        documents: 已加载的知识文档。
        vector_mode: 向量检索模式说明。
        reranker_mode: 精排模式说明。
        capped: 是否因内存上限截断加载。
        embedding_model: 当前配置的向量模型名称。
        reranker_model: 当前配置的精排模型名称。

    Returns:
        可直接返回给前端的知识库统计对象。
    """

    return KnowledgeStats(
        total_documents=len(documents),
        keyword_document_count=len(documents),
        vector_document_count=0,
        source_counts=dict(Counter(document.source for document in documents)),
        trust_counts=dict(Counter(document.trust_level for document in documents)),
        vector_mode=vector_mode,
        embedding_model=embedding_model,
        vector_index_ready=False,
        reranker_mode=reranker_mode,
        reranker_model=reranker_model,
        capped=capped,
    )
