#!/usr/bin/env python3
"""使用外部 qrels 评测 BM25、FAISS、RRF 与 Reranker 各阶段质量。"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.faiss_index import PersistentFaissIndex  # noqa: E402
from app.services.persistent_index import PersistentBM25Index  # noqa: E402
from app.services.reranker import MedicalReranker  # noqa: E402
from app.services.retrieval import reciprocal_rank_fusion  # noqa: E402


@dataclass(frozen=True)
class EvaluationCase:
    """一条由外部标注提供的检索查询和相关文档集合。"""

    query: str
    relevant_document_ids: frozenset[str]


def parse_args() -> argparse.Namespace:
    """解析 qrels、索引、模型和评测截断参数。

    Returns:
        包含评测文件与检索运行配置的参数对象。
    """

    parser = argparse.ArgumentParser(description="评测医疗混合检索各排序阶段。")
    parser.add_argument(
        "--qrels",
        type=Path,
        required=True,
        help="每行包含 query 和 relevant_document_ids 的 JSONL 文件。",
    )
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
    parser.add_argument("--embedding-model", default="ming0302/bge-m3-medical-cn")
    parser.add_argument("--embedding-subfolder", default="model")
    parser.add_argument("--reranker-model", default="BAAI/bge-reranker-v2-m3")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=BACKEND_DIR / "data" / "models",
    )
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--candidate-k", type=int, default=100)
    parser.add_argument("--rrf-k", type=int, default=40)
    parser.add_argument("--nprobe", type=int, default=32)
    return parser.parse_args()


def load_cases(path: Path) -> list[EvaluationCase]:
    """读取并校验医生或标注人员维护的 qrels JSONL。

    Args:
        path: 外部 qrels 文件路径。

    Returns:
        去除空白且至少包含一个相关文档的评测用例列表。

    Raises:
        ValueError: 文件为空或某行字段结构不合法时抛出。
    """

    cases: list[EvaluationCase] = []
    with path.open("r", encoding="utf-8") as source_file:
        for line_number, line in enumerate(source_file, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            query = str(row.get("query") or "").strip()
            relevant = row.get("relevant_document_ids")
            if not query or not isinstance(relevant, list) or not relevant:
                raise ValueError(f"qrels 第 {line_number} 行缺少有效查询或相关文档 ID")
            cases.append(
                EvaluationCase(
                    query=query,
                    relevant_document_ids=frozenset(str(item) for item in relevant),
                )
            )
    if not cases:
        raise ValueError("qrels 中没有可评测用例")
    return cases


def score_ranking(
    ranked_ids: list[str],
    relevant_ids: frozenset[str],
    top_k: int,
) -> dict[str, float]:
    """计算一条排序在指定截断处的 Recall 和倒数排名。

    Args:
        ranked_ids: 按相关性降序排列的文档 ID。
        relevant_ids: 外部标注的全部相关文档 ID。
        top_k: 指标统计的排序截断位置。

    Returns:
        包含 recall 和 reciprocal_rank 的指标字典。
    """

    truncated = ranked_ids[:top_k]
    hit_count = len(set(truncated) & relevant_ids)
    first_rank = next(
        (rank for rank, document_id in enumerate(truncated, start=1) if document_id in relevant_ids),
        None,
    )
    return {
        "recall": hit_count / len(relevant_ids),
        "reciprocal_rank": 1 / first_rank if first_rank else 0.0,
    }


def average_stage_metrics(
    totals: dict[str, dict[str, float]],
    case_count: int,
    top_k: int,
) -> dict[str, dict[str, float]]:
    """把各阶段累计指标转换为平均 Recall@K 和 MRR@K。

    Args:
        totals: 各排序阶段的指标累计值。
        case_count: 有效评测用例数量。
        top_k: 指标截断位置。

    Returns:
        以阶段名称为键的平均指标字典。
    """

    return {
        stage: {
            f"recall@{top_k}": round(values["recall"] / case_count, 6),
            f"mrr@{top_k}": round(values["reciprocal_rank"] / case_count, 6),
        }
        for stage, values in totals.items()
    }


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    """运行四阶段检索并汇总外部相关性标注指标。

    Args:
        args: 命令行解析得到的索引、模型与截断配置。

    Returns:
        可直接序列化为 JSON 的评测摘要与逐查询排名。
    """

    if args.top_k <= 0 or args.candidate_k < args.top_k or args.rrf_k < args.top_k:
        raise ValueError("candidate-k 和 rrf-k 不能小于正数 top-k")
    cases = load_cases(args.qrels)
    bm25 = PersistentBM25Index(args.database)
    vector = PersistentFaissIndex(
        args.faiss_index,
        args.faiss_manifest,
        args.embedding_model,
        model_subfolder=args.embedding_subfolder or None,
        nprobe=args.nprobe,
        cache_dir=args.cache_dir,
    )
    reranker = MedicalReranker(
        args.reranker_model,
        cache_dir=args.cache_dir,
    )
    totals: dict[str, dict[str, float]] = defaultdict(
        lambda: {"recall": 0.0, "reciprocal_rank": 0.0}
    )
    details: list[dict[str, Any]] = []
    try:
        for case in cases:
            bm25_matches = bm25.search(case.query, args.candidate_k)
            vector_rows = vector.search(case.query, args.candidate_k)
            documents = bm25.get_by_rowids([rowid for rowid, _ in vector_rows])
            vector_matches = [
                (documents[rowid], score)
                for rowid, score in vector_rows
                if rowid in documents
            ]
            fused = reciprocal_rank_fusion(
                bm25_matches,
                vector_matches,
                top_k=args.rrf_k,
            )
            reranked = reranker.rerank(case.query, fused)
            rankings = {
                "bm25": [document.id for document, _ in bm25_matches],
                "faiss": [document.id for document, _ in vector_matches],
                "rrf": [candidate.document.id for candidate in fused],
                "reranker": [candidate.document.id for candidate in reranked],
            }
            case_metrics: dict[str, dict[str, float]] = {}
            for stage, ranked_ids in rankings.items():
                metrics = score_ranking(
                    ranked_ids,
                    case.relevant_document_ids,
                    args.top_k,
                )
                case_metrics[stage] = metrics
                for metric, value in metrics.items():
                    totals[stage][metric] += value
            details.append(
                {
                    "query": case.query,
                    "metrics": case_metrics,
                    "top_document_ids": {
                        stage: ranked_ids[: args.top_k]
                        for stage, ranked_ids in rankings.items()
                    },
                }
            )
    finally:
        reranker.close()
        vector.close()
        bm25.close()

    return {
        "case_count": len(cases),
        "top_k": args.top_k,
        "aggregate": average_stage_metrics(totals, len(cases), args.top_k),
        "details": details,
    }


def main() -> None:
    """运行检索评测并以格式化 JSON 输出结果。"""

    try:
        result = evaluate(parse_args())
    except (ImportError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"评测失败：{error}") from error
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
