#!/usr/bin/env python3
"""把分片 JSONL.GZ 构建为可查询的百万级 SQLite FTS5 索引。"""

from __future__ import annotations

import argparse
import ast
import gzip
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.text import tokenize  # noqa: E402


DOCUMENT_COLUMNS = (
    "rowid, document_id, title, question, content, source, source_url, source_type, "
    "trust_level, allow_treatment_generation, regions, minimum_age, maximum_age, "
    "pregnancy_allowed, guideline_version, updated_at, license, retrieval_only, "
    "keywords, cautions"
)


def parse_args() -> argparse.Namespace:
    """解析建索引命令行参数。

    Returns:
        包含数据目录、索引路径、批大小和限量的参数对象。
    """

    parser = argparse.ArgumentParser(description="为医疗 JSONL 分片构建 SQLite FTS5 索引。")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=BACKEND_DIR / "data" / "raw",
        help="Huatuo JSONL.GZ 分片目录。",
    )
    parser.add_argument(
        "--sample-file",
        type=Path,
        default=BACKEND_DIR / "data" / "sample_knowledge.jsonl",
        help="优先写入的演示安全规则文件。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BACKEND_DIR / "data" / "processed" / "knowledge.db",
        help="最终 SQLite 索引文件。",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5_000,
        help="每次事务写入的文档数。",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="最多索引多少条；0 表示索引全部数据。",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="允许替换已经存在的最终索引。",
    )
    return parser.parse_args()


def utc_now() -> str:
    """生成当前 UTC 时间文本。

    Returns:
        ISO 8601 格式的 UTC 时间。
    """

    return datetime.now(timezone.utc).isoformat()


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """逐行读取普通或 gzip 压缩的 JSONL 文件。

    Args:
        path: 输入分片路径。

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


def clean_list_text(value: Any) -> str:
    """清理部分上游数据把字符串列表再次序列化成文本的问题。

    Args:
        value: 原始标题、问题或正文。

    Returns:
        去除列表外壳并连接后的可读文本。
    """

    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(str(item).strip() for item in value if str(item).strip())
    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                return "\n".join(
                    str(item).strip() for item in parsed if str(item).strip()
                )
        except (SyntaxError, ValueError):
            pass
    return text


def json_array(value: Any, default: list[str]) -> str:
    """把不稳定的数组字段转换为统一 JSON 文本。

    Args:
        value: 原始数组、字符串或空值。
        default: 空值时使用的默认数组。

    Returns:
        可写入 SQLite 的 JSON 数组文本。
    """

    normalized = value if isinstance(value, list) else default
    return json.dumps(normalized, ensure_ascii=False)


def create_schema(connection: sqlite3.Connection) -> None:
    """创建文档表、FTS5 虚拟表和构建元数据表。

    Args:
        connection: 新建索引的 SQLite 连接。
    """

    connection.executescript(
        """
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;
        PRAGMA temp_store = MEMORY;
        PRAGMA cache_size = -262144;

        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE documents (
            rowid INTEGER PRIMARY KEY,
            document_id TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            question TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT NOT NULL,
            source_url TEXT,
            source_type TEXT NOT NULL,
            trust_level TEXT NOT NULL,
            allow_treatment_generation INTEGER NOT NULL,
            regions TEXT NOT NULL,
            minimum_age REAL,
            maximum_age REAL,
            pregnancy_allowed INTEGER,
            guideline_version TEXT,
            updated_at TEXT,
            license TEXT,
            retrieval_only INTEGER NOT NULL,
            keywords TEXT NOT NULL,
            cautions TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE document_fts USING fts5(
            search_text,
            tokenize = 'unicode61 remove_diacritics 2'
        );
        """
    )
    connection.executemany(
        "INSERT INTO metadata(key, value) VALUES (?, ?)",
        (("status", "building"), ("started_at", utc_now())),
    )
    connection.commit()


def normalize_row(row: dict[str, Any], rowid: int) -> tuple[tuple[Any, ...], tuple[int, str]] | None:
    """把统一 JSONL 记录转换为文档表行和预分词 FTS 行。

    Args:
        row: JSONL 中的原始记录。
        rowid: 文档在索引中的顺序编号。

    Returns:
        文档表参数和 FTS 表参数；缺少问题或正文时返回空值。
    """

    question = clean_list_text(row.get("question") or row.get("questions"))
    content = clean_list_text(row.get("content") or row.get("answer") or row.get("answers"))
    title = clean_list_text(row.get("title")) or question[:80]
    if not question or not content:
        return None
    keywords = row.get("keywords") if isinstance(row.get("keywords"), list) else []
    search_source = " ".join([title, question, " ".join(str(item) for item in keywords)])
    search_tokens = " ".join(dict.fromkeys(tokenize(search_source)))
    pregnancy_value = row.get("pregnancy_allowed")
    document_values = (
        rowid,
        str(row.get("id") or f"document-{rowid}"),
        title,
        question,
        content,
        str(row.get("source") or "unknown"),
        row.get("source_url"),
        str(row.get("source_type") or "medical_qa"),
        str(row.get("trust_level") or "secondary"),
        int(bool(row.get("allow_treatment_generation", False))),
        json_array(row.get("regions"), ["CN"]),
        row.get("minimum_age"),
        row.get("maximum_age"),
        None if pregnancy_value is None else int(bool(pregnancy_value)),
        row.get("guideline_version"),
        row.get("updated_at"),
        row.get("license"),
        int(bool(row.get("retrieval_only", True))),
        json_array(keywords, []),
        json_array(row.get("cautions"), []),
    )
    return document_values, (rowid, search_tokens)


def flush_batch(
    connection: sqlite3.Connection,
    documents: list[tuple[Any, ...]],
    fts_rows: list[tuple[int, str]],
) -> None:
    """在一个事务中批量写入文档和对应的 FTS 词元。

    Args:
        connection: 目标 SQLite 连接。
        documents: 文档表参数列表。
        fts_rows: FTS5 行号和预分词文本列表。
    """

    if not documents:
        return
    placeholders = ", ".join("?" for _ in range(20))
    connection.executemany(
        f"INSERT INTO documents({DOCUMENT_COLUMNS}) VALUES ({placeholders})",
        documents,
    )
    connection.executemany(
        "INSERT INTO document_fts(rowid, search_text) VALUES (?, ?)",
        fts_rows,
    )
    connection.commit()
    documents.clear()
    fts_rows.clear()


def build_index(args: argparse.Namespace) -> int:
    """遍历全部分片并原子生成最终 SQLite 索引。

    Args:
        args: 已校验的命令行参数。

    Returns:
        成功时返回写入索引的文档总数。

    Raises:
        FileExistsError: 最终索引已存在且未指定强制替换时抛出。
        ValueError: 参数不合法或没有找到输入分片时抛出。
    """

    if args.batch_size <= 0 or args.limit < 0:
        raise ValueError("--batch-size 必须大于 0，--limit 不能为负数")
    if args.output.exists() and not args.force:
        raise FileExistsError(f"索引已存在：{args.output}；如需替换请添加 --force")

    paths = [args.sample_file] if args.sample_file.exists() else []
    paths.extend(sorted(args.raw_dir.glob("*.jsonl.gz")))
    if not paths:
        raise ValueError("没有找到可索引的 JSONL 或 JSONL.GZ 文件")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = args.output.with_suffix(args.output.suffix + ".building")
    if temporary_path.exists():
        temporary_path.unlink()
    connection = sqlite3.connect(temporary_path)
    create_schema(connection)

    document_batch: list[tuple[Any, ...]] = []
    fts_batch: list[tuple[int, str]] = []
    rowid = 0
    skipped = 0
    started_at = time.monotonic()

    try:
        for path in paths:
            for row in iter_jsonl(path):
                normalized = normalize_row(row, rowid + 1)
                if normalized is None:
                    skipped += 1
                    continue
                rowid += 1
                document_values, fts_values = normalized
                document_batch.append(document_values)
                fts_batch.append(fts_values)
                if len(document_batch) >= args.batch_size:
                    flush_batch(connection, document_batch, fts_batch)
                if rowid % 10_000 == 0:
                    elapsed = max(time.monotonic() - started_at, 0.001)
                    print(
                        f"已索引 {rowid:,} 条，速度 {rowid / elapsed:,.0f} 条/秒",
                        flush=True,
                    )
                if args.limit and rowid >= args.limit:
                    break
            if args.limit and rowid >= args.limit:
                break

        flush_batch(connection, document_batch, fts_batch)
        connection.execute("CREATE INDEX documents_source_idx ON documents(source)")
        connection.execute(
            "CREATE INDEX documents_trust_idx ON documents(trust_level)"
        )
        connection.execute("INSERT INTO metadata(key, value) VALUES ('document_count', ?)", (str(rowid),))
        connection.execute("INSERT INTO metadata(key, value) VALUES ('skipped_count', ?)", (str(skipped),))
        connection.execute("INSERT INTO metadata(key, value) VALUES ('completed_at', ?)", (utc_now(),))
        connection.execute("UPDATE metadata SET value = 'complete' WHERE key = 'status'")
        connection.commit()
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        connection.close()

    if args.output.exists():
        args.output.unlink()
    temporary_path.replace(args.output)
    elapsed = time.monotonic() - started_at
    print(
        f"索引完成：{rowid:,} 条，跳过 {skipped:,} 条，耗时 {elapsed:.1f} 秒，文件：{args.output}",
        flush=True,
    )
    return rowid


def main() -> int:
    """执行索引构建并转换为命令行退出码。

    Returns:
        成功返回 0，参数或文件错误返回 1。
    """

    args = parse_args()
    try:
        build_index(args)
        return 0
    except (FileExistsError, OSError, sqlite3.Error, ValueError, json.JSONDecodeError) as error:
        print(f"建索引失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
