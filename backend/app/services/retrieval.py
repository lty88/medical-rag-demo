"""内存 BM25 与跨索引 RRF 混合排序。"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Iterable

from app.models import RankedDocument, SourceDocument
from app.services.text import tokenize


class BM25Retriever:
    """无需额外依赖的 BM25 关键词召回器。"""

    def __init__(
        self,
        documents: list[SourceDocument],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        """预计算文档词频和逆文档频率。

        Args:
            documents: 要建立索引的知识文档。
            k1: 词频饱和参数。
            b: 文档长度归一化参数。
        """

        self.documents = documents
        self.k1 = k1
        self.b = b
        self.tokens = [tokenize(document.searchable_text) for document in documents]
        self.term_frequencies = [Counter(items) for items in self.tokens]
        self.average_length = (
            sum(len(items) for items in self.tokens) / len(self.tokens)
            if self.tokens
            else 1.0
        )
        document_frequencies: Counter[str] = Counter()
        for items in self.tokens:
            document_frequencies.update(set(items))
        document_count = max(len(documents), 1)
        self.idf = {
            term: math.log(1 + (document_count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequencies.items()
        }

    def search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        """按 BM25 分数返回关键词候选。

        Args:
            query: 用户检索文本。
            top_k: 最多返回的候选数量。

        Returns:
            按分数降序排列的文档下标和分数。
        """

        query_terms = list(dict.fromkeys(tokenize(query)))
        scores: list[tuple[int, float]] = []
        for index, frequencies in enumerate(self.term_frequencies):
            document_length = len(self.tokens[index])
            score = 0.0
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * document_length / self.average_length
                )
                score += self.idf.get(term, 0) * frequency * (self.k1 + 1) / denominator
            if score > 0:
                scores.append((index, score))
        return sorted(scores, key=lambda item: item[1], reverse=True)[:top_k]


def reciprocal_rank_fusion(
    bm25_results: Iterable[tuple[SourceDocument, float]],
    vector_results: Iterable[tuple[SourceDocument, float]],
    top_k: int,
    rank_constant: int = 60,
) -> list[RankedDocument]:
    """通过 RRF 合并关键词和向量排序，避免直接比较异构分数。

    Args:
        bm25_results: BM25 独立召回的文档与分数。
        vector_results: FAISS 独立召回的文档与分数。
        top_k: 混排后最多保留的数量。
        rank_constant: RRF 平滑常数。

    Returns:
        包含两路原始分数和 RRF 分数的候选文档。
    """

    scores: defaultdict[str, float] = defaultdict(float)
    ranked: dict[str, RankedDocument] = {}
    for rank, (document, score) in enumerate(bm25_results, start=1):
        scores[document.id] += 1 / (rank_constant + rank)
        ranked[document.id] = RankedDocument(document=document, bm25_score=score)
    for rank, (document, score) in enumerate(vector_results, start=1):
        scores[document.id] += 1 / (rank_constant + rank)
        candidate = ranked.setdefault(
            document.id,
            RankedDocument(document=document),
        )
        candidate.vector_score = score
    ordered_ids = sorted(scores, key=scores.get, reverse=True)[:top_k]
    for document_id in ordered_ids:
        ranked[document_id].rrf_score = scores[document_id]
    return [ranked[document_id] for document_id in ordered_ids]
