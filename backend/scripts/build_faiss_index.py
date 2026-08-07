#!/usr/bin/env python3
"""把全量 SQLite 医疗知识编码为可断点续建的 FAISS IVF-PQ 索引。"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.model_workers import EmbeddingWorkerClient  # noqa: E402
from app.services.embedding_text import (  # noqa: E402
    EMBEDDING_TEXT_VERSION,
    build_embedding_text_from_row,
)


EMBEDDING_COLUMNS = "title, question, content, keywords, source_type"


def parse_args() -> argparse.Namespace:
    """解析全量向量建库命令行参数。

    Returns:
        包含数据库、模型、索引结构和断点配置的参数对象。
    """

    parser = argparse.ArgumentParser(description="构建中文医疗全量 FAISS 索引。")
    parser.add_argument(
        "--database",
        type=Path,
        default=BACKEND_DIR / "data" / "processed" / "knowledge.db",
        help="已经完成的 SQLite 全量知识索引。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BACKEND_DIR / "data" / "processed" / "medical.faiss",
        help="最终 FAISS 索引路径。",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=BACKEND_DIR / "data" / "processed" / "medical.faiss.json",
        help="最终 FAISS 构建清单路径。",
    )
    parser.add_argument(
        "--model",
        default="ming0302/bge-m3-medical-cn",
        help="中文医疗 Embedding 模型名称或本地目录。",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=BACKEND_DIR / "data" / "models",
        help="Hugging Face 模型权重缓存目录。",
    )
    parser.add_argument(
        "--model-subfolder",
        default="model",
        help="模型权重位于仓库内的子目录；根目录模型传空字符串。",
    )
    parser.add_argument("--device", default="auto", help="auto、mps、cuda 或 cpu。")
    parser.add_argument("--batch-size", type=int, default=32, help="模型编码批大小。")
    parser.add_argument(
        "--fetch-size",
        type=int,
        default=2_048,
        help="每次从 SQLite 预取并按长度分桶的文档数。",
    )
    parser.add_argument(
        "--document-max-length",
        type=int,
        default=256,
        help="知识正文编码的最大词元数。",
    )
    parser.add_argument("--nlist", type=int, default=2048, help="IVF 倒排分区数量。")
    parser.add_argument("--pq-m", type=int, default=64, help="PQ 子量化器数量。")
    parser.add_argument("--pq-bits", type=int, default=8, help="每个 PQ 编码的位数。")
    parser.add_argument(
        "--training-sample-size",
        type=int,
        default=100_000,
        help="训练 IVF-PQ 码本的均匀采样文档数。",
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=25_000,
        help="每新增多少条文档持久化一次断点。",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="仅用于局部验证的文档上限；0 表示数据库全量。",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="从 .building 索引断点继续编码。",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="丢弃已有最终索引和构建断点后重新开始。",
    )
    return parser.parse_args()


def utc_now() -> str:
    """生成当前 UTC 时间文本。

    Returns:
        ISO 8601 格式的 UTC 时间。
    """

    return datetime.now(timezone.utc).isoformat()


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """通过临时文件原子写入 UTF-8 JSON 清单。

    Args:
        path: 目标清单路径。
        payload: 要序列化的构建状态字典。
    """

    temporary_path = path.with_name(f"{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary_path, path)


def read_database_count(connection: sqlite3.Connection) -> int:
    """读取 SQLite 文档总数并验证行号连续性。

    Args:
        connection: 全量知识数据库只读连接。

    Returns:
        数据库中的文档总数。

    Raises:
        ValueError: rowid 不是从 1 开始连续排列时抛出。
    """

    row = connection.execute(
        "SELECT COUNT(*) AS count, MIN(rowid) AS minimum, MAX(rowid) AS maximum "
        "FROM documents"
    ).fetchone()
    document_count = int(row["count"])
    if document_count and (int(row["minimum"]) != 1 or int(row["maximum"]) != document_count):
        raise ValueError("SQLite 文档 rowid 不连续，不能安全绑定 FAISS 外部 ID")
    return document_count


def choose_pq_subquantizers(dimension: int, requested_m: int) -> int:
    """选择能够整除向量维度的最大 PQ 子量化器数量。

    Args:
        dimension: Embedding 模型输出维度。
        requested_m: 用户期望的 PQ 子量化器数量。

    Returns:
        不超过期望值且能整除向量维度的正整数。

    Raises:
        ValueError: 请求值不是正整数时抛出。
    """

    if requested_m <= 0:
        raise ValueError("PQ 子量化器数量必须大于 0")
    for candidate in range(min(dimension, requested_m), 0, -1):
        if dimension % candidate == 0:
            return candidate
    return 1


def sample_training_texts(
    connection: sqlite3.Connection,
    target_count: int,
    sample_size: int,
    evidence_content_character_limit: int,
) -> list[str]:
    """按 rowid 均匀采样用于训练 IVF-PQ 码本的分类型向量文本。

    Args:
        connection: 全量知识数据库只读连接。
        target_count: 本次计划写入索引的文档总数。
        sample_size: 期望采样的最大文档数。
        evidence_content_character_limit: 非问答证据正文允许参与编码的字符数。

    Returns:
        按资料类型生成的医疗检索文本列表。
    """

    effective_size = min(target_count, sample_size)
    stride = max(target_count // max(effective_size, 1), 1)
    rows = connection.execute(
        f"SELECT {EMBEDDING_COLUMNS} FROM documents "
        "WHERE rowid <= ? AND rowid % ? = 0 ORDER BY rowid LIMIT ?",
        (target_count, stride, effective_size),
    ).fetchall()
    if len(rows) < effective_size:
        rows = connection.execute(
            f"SELECT {EMBEDDING_COLUMNS} FROM documents "
            "WHERE rowid <= ? ORDER BY rowid LIMIT ?",
            (target_count, effective_size),
        ).fetchall()
    return [
        build_embedding_text_from_row(row, evidence_content_character_limit)
        for row in rows
    ]


def encode_training_vectors(
    encoder: EmbeddingWorkerClient,
    texts: list[str],
    batch_size: int,
) -> Any:
    """分块编码训练样本并持续输出进度，避免长时间无反馈。

    Args:
        encoder: 隔离进程中的中文医疗向量编码器客户端。
        texts: 用于训练 IVF-PQ 的采样正文。
        batch_size: 单次模型推理的文本数量。

    Returns:
        拼接后的连续 float32 训练向量矩阵。
    """

    import numpy as np

    ordered_texts = sorted(texts, key=len)
    chunk_size = max(batch_size * 16, 512)
    chunks: list[Any] = []
    started_at = time.perf_counter()
    for start in range(0, len(ordered_texts), chunk_size):
        chunk = ordered_texts[start : start + chunk_size]
        chunks.append(encoder.encode_documents(chunk, batch_size=batch_size))
        completed = min(start + len(chunk), len(ordered_texts))
        elapsed = max(time.perf_counter() - started_at, 0.001)
        print(
            f"训练样本编码 {completed:,}/{len(ordered_texts):,} "
            f"({completed / len(ordered_texts):.1%})，{completed / elapsed:.1f} 条/秒",
            flush=True,
        )
    return np.ascontiguousarray(np.concatenate(chunks, axis=0), dtype="float32")


def create_trained_index(
    connection: sqlite3.Connection,
    encoder: EmbeddingWorkerClient,
    target_count: int,
    args: argparse.Namespace,
    faiss_module: Any,
) -> tuple[Any, dict[str, int]]:
    """采样训练 IVF-PQ，并用 IDMap2 保留 SQLite rowid。

    Args:
        connection: 全量知识数据库只读连接。
        encoder: 隔离进程中的中文医疗向量编码器客户端。
        target_count: 本次计划写入索引的文档总数。
        args: 命令行索引结构与批大小配置。
        faiss_module: 已导入的 FAISS 模块。

    Returns:
        已训练但尚未写入文档的索引，以及实际使用的结构参数。
    """

    training_texts = sample_training_texts(
        connection,
        target_count,
        args.training_sample_size,
        args.document_max_length * 4,
    )
    if len(training_texts) < 256:
        raise ValueError("训练 IVF-PQ 至少需要 256 条文档")
    effective_nlist = min(args.nlist, max(1, len(training_texts) // 39))
    effective_m = choose_pq_subquantizers(encoder.dimension, args.pq_m)
    print(
        f"训练 IVF-PQ：样本 {len(training_texts):,}，维度 {encoder.dimension}，"
        f"nlist={effective_nlist}，m={effective_m}，bits={args.pq_bits}",
        flush=True,
    )
    started_at = time.perf_counter()
    training_vectors = encode_training_vectors(
        encoder,
        training_texts,
        args.batch_size,
    )
    quantizer = faiss_module.IndexFlatIP(encoder.dimension)
    base_index = faiss_module.IndexIVFPQ(
        quantizer,
        encoder.dimension,
        effective_nlist,
        effective_m,
        args.pq_bits,
        faiss_module.METRIC_INNER_PRODUCT,
    )
    base_index.train(training_vectors)
    index = faiss_module.IndexIDMap2(base_index)
    elapsed = time.perf_counter() - started_at
    print(f"IVF-PQ 训练完成，耗时 {elapsed / 60:.1f} 分钟", flush=True)
    return index, {
        "nlist": effective_nlist,
        "pq_m": effective_m,
        "pq_bits": args.pq_bits,
    }


def maximum_external_id(index: Any, faiss_module: Any) -> int:
    """从 IDMap2 中恢复已经写入的最大 SQLite rowid。

    Args:
        index: 已加载的 FAISS IDMap2 索引。
        faiss_module: 已导入的 FAISS 模块。

    Returns:
        已写入的最大外部 ID；空索引返回 0。
    """

    if int(index.ntotal) == 0:
        return 0
    identifiers = faiss_module.vector_to_array(index.id_map)
    return int(identifiers.max())


def checkpoint_index(
    index: Any,
    index_path: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
    faiss_module: Any,
) -> None:
    """持久化可恢复的 FAISS 二进制与对应构建清单。

    Args:
        index: 当前已经写入部分文档的 FAISS 索引。
        index_path: `.building` 二进制索引路径。
        manifest_path: `.building` 构建清单路径。
        manifest: 当前构建状态字典。
        faiss_module: 已导入的 FAISS 模块。
    """

    temporary_index = index_path.with_name(f"{index_path.name}.tmp")
    faiss_module.write_index(index, str(temporary_index))
    os.replace(temporary_index, index_path)
    write_json_atomic(manifest_path, manifest)


def load_or_create_index(
    args: argparse.Namespace,
    connection: sqlite3.Connection,
    encoder: EmbeddingWorkerClient,
    target_count: int,
    building_index: Path,
    building_manifest: Path,
    faiss_module: Any,
) -> tuple[Any, dict[str, Any], int]:
    """创建新索引或从完整断点恢复构建状态。

    Args:
        args: 命令行构建配置。
        connection: 全量知识数据库只读连接。
        encoder: 隔离进程中的中文医疗向量编码器客户端。
        target_count: 本次计划写入索引的文档总数。
        building_index: 构建中的 FAISS 二进制路径。
        building_manifest: 构建中的清单路径。
        faiss_module: 已导入的 FAISS 模块。

    Returns:
        索引对象、构建清单和已经写入的最大 rowid。

    Raises:
        ValueError: 断点配置与本次参数不一致时抛出。
    """

    if args.resume:
        if not building_index.is_file() or not building_manifest.is_file():
            raise ValueError("没有找到可恢复的 .building 索引和清单")
        manifest = json.loads(building_manifest.read_text(encoding="utf-8"))
        expected = {
            "embedding_model": args.model,
            "embedding_model_subfolder": args.model_subfolder or None,
            "embedding_text_version": EMBEDDING_TEXT_VERSION,
            "document_max_length": args.document_max_length,
            "target_document_count": target_count,
        }
        for key, value in expected.items():
            if manifest.get(key) != value:
                raise ValueError(f"断点参数不一致：{key}")
        index = faiss_module.read_index(str(building_index))
        indexed_through = maximum_external_id(index, faiss_module)
        manifest["indexed_through_rowid"] = indexed_through
        manifest["document_count"] = int(index.ntotal)
        print(
            f"从断点继续：已写入 {int(index.ntotal):,} 条，最大 rowid={indexed_through:,}",
            flush=True,
        )
        return index, manifest, indexed_through

    index, structure = create_trained_index(
        connection,
        encoder,
        target_count,
        args,
        faiss_module,
    )
    manifest: dict[str, Any] = {
        "schema_version": 2,
        "status": "building",
        "index_type": "IndexIDMap2(IndexIVFPQ)",
        "similarity": "cosine-inner-product",
        "text_field": "source_aware_embedding_text",
        "embedding_text_version": EMBEDDING_TEXT_VERSION,
        "embedding_text_rule": {
            "medical_qa": ["question", "title", "keywords"],
            "evidence": ["title", "question", "keywords", "content_excerpt"],
        },
        "embedding_model": args.model,
        "embedding_model_subfolder": args.model_subfolder or None,
        "embedding_dimension": encoder.dimension,
        "document_max_length": args.document_max_length,
        "target_document_count": target_count,
        "document_count": 0,
        "indexed_through_rowid": 0,
        "started_at": utc_now(),
        **structure,
    }
    checkpoint_index(
        index,
        building_index,
        building_manifest,
        manifest,
        faiss_module,
    )
    return index, manifest, 0


def remove_existing_outputs(paths: list[Path]) -> None:
    """删除 `--force` 明确授权覆盖的索引产物。

    Args:
        paths: 允许删除的最终文件和构建断点路径。
    """

    for path in paths:
        if path.is_file():
            path.unlink()


def build_index(args: argparse.Namespace) -> None:
    """执行全量中文医疗向量编码、断点保存和原子发布。

    Args:
        args: 命令行解析得到的构建参数。

    Raises:
        ValueError: 数据库、输出状态或构建参数不合法时抛出。
    """

    import faiss
    import numpy as np

    if args.batch_size <= 0 or args.fetch_size <= 0 or args.checkpoint_every <= 0:
        raise ValueError("批大小、预取数量和断点间隔必须大于 0")
    if args.fetch_size < args.batch_size:
        raise ValueError("SQLite 预取数量不能小于模型批大小")
    if args.resume and args.force:
        raise ValueError("--resume 和 --force 不能同时使用")
    if not args.database.is_file():
        raise ValueError(f"知识数据库不存在：{args.database}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    building_index = Path(f"{args.output}.building")
    building_manifest = Path(f"{args.manifest}.building")
    if args.force:
        remove_existing_outputs(
            [args.output, args.manifest, building_index, building_manifest]
        )
    elif not args.resume and (
        args.output.exists()
        or args.manifest.exists()
        or building_index.exists()
        or building_manifest.exists()
    ):
        raise ValueError("索引产物已存在；继续断点请加 --resume，重建请加 --force")

    connection = sqlite3.connect(
        f"file:{args.database.resolve()}?mode=ro",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    encoder: EmbeddingWorkerClient | None = None
    try:
        database_count = read_database_count(connection)
        target_count = min(database_count, args.limit) if args.limit > 0 else database_count
        if target_count < 256:
            raise ValueError("向量索引至少需要 256 条文档")
        print(
            f"准备编码 {target_count:,}/{database_count:,} 条医疗知识，模型：{args.model}",
            flush=True,
        )
        args.cache_dir.mkdir(parents=True, exist_ok=True)
        encoder = EmbeddingWorkerClient(
            args.model,
            device=args.device,
            document_max_length=args.document_max_length,
            cache_dir=args.cache_dir,
            subfolder=args.model_subfolder or None,
        )
        print(
            f"模型已加载：device={encoder.device}，dimension={encoder.dimension}",
            flush=True,
        )
        index, manifest, indexed_through = load_or_create_index(
            args,
            connection,
            encoder,
            target_count,
            building_index,
            building_manifest,
            faiss,
        )

        build_started_at = time.perf_counter()
        build_start_count = int(index.ntotal)
        last_checkpoint_count = int(index.ntotal)
        last_progress_at = build_started_at
        while indexed_through < target_count:
            rows = connection.execute(
                f"SELECT rowid, {EMBEDDING_COLUMNS} FROM documents "
                "WHERE rowid > ? AND rowid <= ? ORDER BY rowid LIMIT ?",
                (indexed_through, target_count, args.fetch_size),
            ).fetchall()
            if not rows:
                break
            text_rows = [
                (
                    row,
                    build_embedding_text_from_row(
                        row,
                        args.document_max_length * 4,
                    ),
                )
                for row in rows
            ]
            ordered_text_rows = sorted(text_rows, key=lambda item: len(item[1]))
            ordered_rows = [item[0] for item in ordered_text_rows]
            texts = [item[1] for item in ordered_text_rows]
            vectors = encoder.encode_documents(texts, batch_size=args.batch_size)
            identifiers = np.asarray(
                [int(row["rowid"]) for row in ordered_rows],
                dtype="int64",
            )
            index.add_with_ids(vectors, identifiers)
            indexed_through = int(identifiers.max())
            manifest["document_count"] = int(index.ntotal)
            manifest["indexed_through_rowid"] = indexed_through
            manifest["updated_at"] = utc_now()

            now = time.perf_counter()
            if now - last_progress_at >= 30:
                processed_this_run = int(index.ntotal) - build_start_count
                elapsed = max(now - build_started_at, 0.001)
                speed = processed_this_run / elapsed
                remaining_seconds = (target_count - int(index.ntotal)) / max(speed, 0.001)
                print(
                    f"编码进行中 {int(index.ntotal):,}/{target_count:,} "
                    f"({int(index.ntotal) / target_count:.1%})，{speed:.1f} 条/秒，"
                    f"预计剩余 {remaining_seconds / 60:.1f} 分钟",
                    flush=True,
                )
                last_progress_at = now

            if (
                int(index.ntotal) - last_checkpoint_count >= args.checkpoint_every
                or indexed_through >= target_count
            ):
                checkpoint_index(
                    index,
                    building_index,
                    building_manifest,
                    manifest,
                    faiss,
                )
                last_checkpoint_count = int(index.ntotal)
                elapsed = max(time.perf_counter() - build_started_at, 0.001)
                processed = int(index.ntotal)
                speed = (processed - build_start_count) / elapsed
                remaining_seconds = (target_count - processed) / max(speed, 0.001)
                print(
                    f"已编码 {processed:,}/{target_count:,} 条 "
                    f"({processed / target_count:.1%})，{speed:.1f} 条/秒，"
                    f"预计剩余 {remaining_seconds / 60:.1f} 分钟",
                    flush=True,
                )

        if int(index.ntotal) != target_count or indexed_through != target_count:
            raise ValueError(
                f"构建未覆盖目标全量：ntotal={int(index.ntotal)}，rowid={indexed_through}"
            )
        manifest.update(
            {
                "status": "complete",
                "document_count": int(index.ntotal),
                "indexed_through_rowid": indexed_through,
                "source_database": str(args.database.resolve()),
                "source_database_document_count": database_count,
                "completed_at": utc_now(),
            }
        )
        checkpoint_index(
            index,
            building_index,
            building_manifest,
            manifest,
            faiss,
        )
        os.replace(building_index, args.output)
        os.replace(building_manifest, args.manifest)
        print(
            f"全量 FAISS 索引完成：{args.output}，共 {int(index.ntotal):,} 条",
            flush=True,
        )
    finally:
        if encoder is not None:
            encoder.close()
        connection.close()


def main() -> None:
    """运行命令行建库流程，并把参数错误转换为清晰退出信息。"""

    try:
        build_index(parse_args())
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        raise SystemExit(f"构建失败：{error}") from error


if __name__ == "__main__":
    main()
