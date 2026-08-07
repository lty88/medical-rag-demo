#!/usr/bin/env python3
"""并排检查全量 BM25、FAISS 与 RRF 的实际召回结果。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models import SourceDocument  # noqa: E402
from app.services.faiss_index import PersistentFaissIndex  # noqa: E402
from app.services.persistent_index import PersistentBM25Index  # noqa: E402
from app.services.reranker import MedicalReranker  # noqa: E402
from app.services.retrieval import reciprocal_rank_fusion  # noqa: E402


def parse_args() -> argparse.Namespace:
    """解析检索检查命令的查询、索引和展示参数。

    Returns:
        包含查询文本、索引路径、模型配置和候选数的参数对象。
    """

    parser = argparse.ArgumentParser(description="检查 BM25/FAISS/RRF 召回结果。")
    parser.add_argument("query", help="要检查的中文医疗查询。")
    parser.add_argument(
        "--database",
        type=Path,
        default=BACKEND_DIR / "data" / "processed" / "knowledge.db",
    )
    parser.add_argument(
        "--faiss-index",
        type=Path,
        default=BACKEND_DIR / "data" / "processed" / "medical.faiss",
    )
    parser.add_argument(
        "--faiss-manifest",
        type=Path,
        default=BACKEND_DIR / "data" / "processed" / "medical.faiss.json",
    )
    parser.add_argument("--model", default="ming0302/bge-m3-medical-cn")
    parser.add_argument("--model-subfolder", default="model")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=BACKEND_DIR / "data" / "models",
    )
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--nprobe", type=int, default=32)
    parser.add_argument(
        "--reranker-model",
        default="BAAI/bge-reranker-v2-m3",
    )
    parser.add_argument(
        "--skip-reranker",
        action="store_true",
        help="只检查两路召回和 RRF，不加载 Cross-Encoder。",
    )
    return parser.parse_args()


def print_results(
    label: str,
    matches: list[tuple[SourceDocument, float]],
) -> None:
    """以紧凑文本输出一路召回的标题、问题和分数。

    Args:
        label: 当前召回或排序阶段名称。
        matches: 文档对象与阶段分数组成的列表。
    """

    print(f"\n[{label}]", flush=True)
    for rank, (document, score) in enumerate(matches, start=1):
        print(
            f"{rank:02d}. {score:.6f} | {document.id} | "
            f"{document.question or document.title}",
            flush=True,
        )


def inspect(args: argparse.Namespace) -> None:
    """执行两路独立召回、文档回表和 RRF 混排并输出结果。

    Args:
        args: 命令行解析得到的检索检查参数。
    """

    bm25 = PersistentBM25Index(args.database)
    vector = PersistentFaissIndex(
        args.faiss_index,
        args.faiss_manifest,
        args.model,
        model_subfolder=args.model_subfolder or None,
        nprobe=args.nprobe,
        cache_dir=args.cache_dir,
    )
    reranker = (
        None
        if args.skip_reranker
        else MedicalReranker(
            args.reranker_model,
            cache_dir=args.cache_dir,
        )
    )
    try:
        bm25_matches = bm25.search(args.query, args.top_k)
        vector_rows = vector.search(args.query, args.top_k)
        documents = bm25.get_by_rowids([rowid for rowid, _ in vector_rows])
        vector_matches = [
            (documents[rowid], score)
            for rowid, score in vector_rows
            if rowid in documents
        ]
        fused = reciprocal_rank_fusion(
            bm25_matches,
            vector_matches,
            top_k=args.top_k,
        )
        print_results("BM25 独立召回", bm25_matches)
        print_results("FAISS 独立召回", vector_matches)
        print_results(
            "RRF 混排",
            [(candidate.document, candidate.rrf_score) for candidate in fused],
        )
        if reranker is not None:
            reranked = reranker.rerank(args.query, fused)
            print_results(
                f"Cross-Encoder 精排 / {reranker.mode}",
                [
                    (candidate.document, candidate.rerank_score)
                    for candidate in reranked
                ],
            )
    finally:
        if reranker is not None:
            reranker.close()
        vector.close()
        bm25.close()


def main() -> None:
    """运行检索检查命令并把常见索引错误转换为清晰退出信息。"""

    try:
        inspect(parse_args())
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        raise SystemExit(f"检查失败：{error}") from error


if __name__ == "__main__":
    main()
