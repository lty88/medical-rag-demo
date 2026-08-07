"""面向百万级语料的 SQLite FTS5 持久化关键词索引。"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.models import SourceDocument
from app.services.text import tokenize


def build_fts_query(query: str) -> str:
    """把自然语言查询转换为安全的 FTS5 OR 表达式。

    Args:
        query: 用户原始查询。

    Returns:
        由中文双字片段和英文词组成的 FTS5 查询。
    """

    terms = [term for term in dict.fromkeys(tokenize(query)) if len(term) >= 2]
    escaped = [f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms[:80]]
    return " OR ".join(escaped)


def _json_list(value: str | None, default: list[str]) -> list[str]:
    """把数据库中的 JSON 数组安全还原为字符串列表。

    Args:
        value: 数据库存储的 JSON 文本。
        default: 空值或解析失败时使用的默认列表。

    Returns:
        解析后的字符串列表。
    """

    if not value:
        return default
    try:
        parsed = json.loads(value)
        return [str(item) for item in parsed] if isinstance(parsed, list) else default
    except json.JSONDecodeError:
        return default


class PersistentBM25Index:
    """只读访问离线构建的 SQLite FTS5 全量索引。"""

    def __init__(self, path: Path) -> None:
        """打开索引并验证其构建状态。

        Args:
            path: SQLite 索引文件路径。

        Raises:
            ValueError: 索引不存在、结构不完整或尚未构建完成时抛出。
        """

        if not path.exists():
            raise ValueError(f"索引不存在：{path}")
        self.path = path
        self.connection = sqlite3.connect(
            f"file:{path}?mode=ro",
            uri=True,
            check_same_thread=False,
        )
        self.connection.row_factory = sqlite3.Row
        status = self.connection.execute(
            "SELECT value FROM metadata WHERE key = 'status'"
        ).fetchone()
        if status is None or status["value"] != "complete":
            self.connection.close()
            raise ValueError("索引尚未构建完成")

    @property
    def document_count(self) -> int:
        """返回全量索引中的文档数。

        Returns:
            已成功写入索引的文档数量。
        """

        row = self.connection.execute(
            "SELECT value FROM metadata WHERE key = 'document_count'"
        ).fetchone()
        return int(row["value"]) if row else 0

    def search(self, query: str, top_k: int) -> list[tuple[SourceDocument, float]]:
        """在全量 FTS5 索引中执行 BM25 检索。

        Args:
            query: 用户自然语言查询。
            top_k: 最多返回的候选文档数。

        Returns:
            按 BM25 相关度降序排列的文档和正向分数。
        """

        fts_query = build_fts_query(query)
        if not fts_query:
            return []
        rows = self.connection.execute(
            """
            SELECT d.*, bm25(document_fts) AS rank_score
            FROM document_fts
            JOIN documents AS d ON d.rowid = document_fts.rowid
            WHERE document_fts MATCH ?
            ORDER BY rank_score
            LIMIT ?
            """,
            (fts_query, top_k),
        ).fetchall()
        return [(self._to_document(row), -float(row["rank_score"])) for row in rows]

    def get_by_rowids(self, rowids: list[int]) -> dict[int, SourceDocument]:
        """按 SQLite 行号批量读取向量召回命中的文档。

        Args:
            rowids: FAISS 返回的 SQLite 文档行号。

        Returns:
            以行号为键、统一知识文档为值的字典。
        """

        normalized = list(dict.fromkeys(rowid for rowid in rowids if rowid > 0))
        if not normalized:
            return {}
        placeholders = ", ".join("?" for _ in normalized)
        rows = self.connection.execute(
            f"SELECT * FROM documents WHERE rowid IN ({placeholders})",
            normalized,
        ).fetchall()
        return {int(row["rowid"]): self._to_document(row) for row in rows}

    def source_counts(self) -> dict[str, int]:
        """统计全量索引中的数据来源分布。

        Returns:
            以来源名称为键、文档数为值的字典。
        """

        rows = self.connection.execute(
            "SELECT source, COUNT(*) AS count FROM documents GROUP BY source"
        ).fetchall()
        return {str(row["source"]): int(row["count"]) for row in rows}

    def trust_counts(self) -> dict[str, int]:
        """统计全量索引中的可信等级分布。

        Returns:
            以可信等级为键、文档数为值的字典。
        """

        rows = self.connection.execute(
            "SELECT trust_level, COUNT(*) AS count FROM documents GROUP BY trust_level"
        ).fetchall()
        return {str(row["trust_level"]): int(row["count"]) for row in rows}

    def close(self) -> None:
        """关闭只读数据库连接。"""

        self.connection.close()

    def _to_document(self, row: sqlite3.Row) -> SourceDocument:
        """把数据库行转换为统一知识文档。

        Args:
            row: SQLite 查询返回的文档行。

        Returns:
            可继续参与精排、过滤和引用展示的知识文档。
        """

        pregnancy_value: Any = row["pregnancy_allowed"]
        return SourceDocument(
            id=str(row["document_id"]),
            title=str(row["title"]),
            question=str(row["question"]),
            content=str(row["content"]),
            source=str(row["source"]),
            source_url=row["source_url"],
            source_type=str(row["source_type"]),
            trust_level=str(row["trust_level"]),
            allow_treatment_generation=bool(row["allow_treatment_generation"]),
            regions=_json_list(row["regions"], ["CN"]),
            minimum_age=row["minimum_age"],
            maximum_age=row["maximum_age"],
            pregnancy_allowed=(
                None if pregnancy_value is None else bool(pregnancy_value)
            ),
            guideline_version=row["guideline_version"],
            updated_at=row["updated_at"],
            license=row["license"],
            retrieval_only=bool(row["retrieval_only"]),
            keywords=_json_list(row["keywords"], []),
            cautions=_json_list(row["cautions"], []),
        )
