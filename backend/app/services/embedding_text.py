"""按医疗资料类型生成适合稠密向量召回的文本。"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


EMBEDDING_TEXT_VERSION = "source-aware-question-first-v1"
QUESTION_FIRST_SOURCE_TYPES = frozenset(
    {
        "medical_qa",
        "consultation_qa",
        "medical_dialogue",
    }
)


def parse_keywords(value: Any) -> list[str]:
    """把数据库中的关键词字段解析为清理后的字符串列表。

    Args:
        value: JSON 字符串、字符串列表或空值。

    Returns:
        去除空白和空项后的关键词列表。
    """

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = [value]
    elif isinstance(value, (list, tuple)):
        parsed = value
    else:
        parsed = []
    if not isinstance(parsed, (list, tuple)):
        parsed = [parsed]
    return [str(item).strip() for item in parsed if str(item).strip()]


def append_unique_segment(segments: list[str], value: Any) -> None:
    """追加非空且未被已有长文本覆盖的检索片段。

    Args:
        segments: 已经收集的检索文本片段。
        value: 等待清理和去重的标题、问题、关键词或正文。
    """

    cleaned = " ".join(str(value or "").split())
    if not cleaned:
        return
    if any(cleaned == existing or cleaned in existing for existing in segments):
        return
    segments.append(cleaned)


def build_embedding_text(
    *,
    title: Any,
    question: Any,
    content: Any,
    keywords: Any,
    source_type: Any,
    evidence_content_character_limit: int,
) -> str:
    """按资料类型构造用于 FAISS 的语义召回文本。

    问答和问诊数据只编码问题、标题与关键词，避免长答案稀释用户症状语义；
    指南、说明书、规则等证据文档会额外编码受限长度的正文片段。

    Args:
        title: 文档标题。
        question: 问答问题或证据章节问题。
        content: 完整回答或证据正文。
        keywords: JSON 字符串或关键词列表。
        source_type: 用于选择问答或证据规则的资料类型。
        evidence_content_character_limit: 证据正文允许参与向量文本的最大字符数。

    Returns:
        清理、去重并按类型拼接后的向量文本。

    Raises:
        ValueError: 证据正文字符上限不是正整数时抛出。
    """

    if evidence_content_character_limit <= 0:
        raise ValueError("证据正文字符上限必须大于 0")

    normalized_source_type = str(source_type or "").strip().lower()
    keyword_items = parse_keywords(keywords)
    segments: list[str] = []

    if normalized_source_type in QUESTION_FIRST_SOURCE_TYPES:
        append_unique_segment(segments, question)
        append_unique_segment(segments, title)
        for keyword in keyword_items:
            append_unique_segment(segments, keyword)
        if not segments:
            append_unique_segment(segments, str(content or "")[:evidence_content_character_limit])
    else:
        append_unique_segment(segments, title)
        append_unique_segment(segments, question)
        for keyword in keyword_items:
            append_unique_segment(segments, keyword)
        append_unique_segment(
            segments,
            str(content or "")[:evidence_content_character_limit],
        )

    return "\n".join(segments)


def build_embedding_text_from_row(
    row: Mapping[str, Any],
    evidence_content_character_limit: int,
) -> str:
    """从 SQLite 行记录生成分类型向量文本。

    Args:
        row: 包含标题、问题、正文、关键词和资料类型的数据库行。
        evidence_content_character_limit: 证据正文允许参与向量文本的最大字符数。

    Returns:
        可直接交给医疗 Embedding 模型的文本。
    """

    return build_embedding_text(
        title=row["title"],
        question=row["question"],
        content=row["content"],
        keywords=row["keywords"],
        source_type=row["source_type"],
        evidence_content_character_limit=evidence_content_character_limit,
    )
