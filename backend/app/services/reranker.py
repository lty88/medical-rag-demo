"""真实 Cross-Encoder 医疗候选精排与证据策略。"""

from __future__ import annotations

from pathlib import Path

from app.models import RankedDocument
from app.services.model_workers import RerankerWorkerClient
from app.services.text import contains_any, tokenize


TREATMENT_TERMS = {
    "吃什么药",
    "用什么药",
    "怎么治疗",
    "治疗方案",
    "剂量",
    "用法用量",
    "处方",
    "停药",
    "加量",
    "减量",
}
TRUST_BOOST = {
    "primary": 0.32,
    "high": 0.28,
    "secondary": 0.12,
    "medium": 0.1,
    "demo": 0.04,
    "low": 0.0,
}


def is_treatment_intent(query: str) -> bool:
    """判断用户是否在请求治疗、处方或剂量建议。

    Args:
        query: 用户症状与问题文本。

    Returns:
        命中治疗意图关键词时返回真。
    """

    return contains_any(query, TREATMENT_TERMS)


class MedicalReranker:
    """使用 BGE Cross-Encoder 精排，并叠加可审计的医疗证据策略。"""

    def __init__(
        self,
        model_name: str | None = None,
        device: str = "auto",
        max_length: int = 512,
        batch_size: int = 8,
        cache_dir: Path | None = None,
    ) -> None:
        """加载真实 Reranker；依赖缺失时保留显式的策略回退状态。

        Args:
            model_name: Hugging Face Reranker 名称或本地模型目录。
            device: 模型推理设备，auto 会按硬件能力选择。
            max_length: 查询与候选拼接后的最大词元数。
            batch_size: 单次 Cross-Encoder 推理的候选数量。
            cache_dir: Reranker 模型权重缓存目录。
        """

        self.model_name = model_name
        self.max_length = max_length
        self.batch_size = batch_size
        self.worker: RerankerWorkerClient | None = None
        self.load_error: str | None = None
        if not model_name:
            return
        try:
            self.worker = RerankerWorkerClient(
                model_name,
                device=device,
                max_length=max_length,
                batch_size=batch_size,
                cache_dir=cache_dir,
            )
        except Exception as error:  # 可选模型边界必须把离线与兼容性错误转为显式状态
            self.worker = None
            self.load_error = f"{type(error).__name__}: {error}"

    @property
    def mode(self) -> str:
        """返回当前实际使用的精排模式。

        Returns:
            真实模型名称或明确的策略回退说明。
        """

        if self.worker is not None:
            return f"Cross-Encoder {self.model_name} + 医疗证据策略"
        if self.model_name:
            return f"Reranker 不可用（已配置 {self.model_name}）+ 医疗策略回退"
        return "未配置 Reranker + 医疗策略回退"

    @property
    def neural_available(self) -> bool:
        """判断真实 Cross-Encoder 是否已经成功加载。

        Returns:
            模型和分词器均可用时返回真。
        """

        return self.worker is not None

    def rerank(
        self, query: str, candidates: list[RankedDocument]
    ) -> list[RankedDocument]:
        """综合 Cross-Encoder 相关性、来源可信度与治疗权限重新排序。

        Args:
            query: 用户检索文本。
            candidates: RRF 混排后的有限候选集合。

        Returns:
            按医疗精排分数降序排列的候选列表。
        """

        model_scores: list[float] | None = None
        if self.neural_available:
            try:
                model_scores = self._predict(query, candidates)
            except RuntimeError as error:
                self.load_error = str(error)
                self.close()
        treatment_intent = is_treatment_intent(query)
        query_tokens = set(tokenize(query))
        for index, candidate in enumerate(candidates):
            if model_scores is None:
                document_tokens = set(tokenize(candidate.document.searchable_text))
                base_score = len(query_tokens & document_tokens) / max(len(query_tokens), 1)
            else:
                base_score = model_scores[index]
            trust_score = TRUST_BOOST.get(candidate.document.trust_level, 0)
            treatment_score = 0.2 if (
                treatment_intent and candidate.document.allow_treatment_generation
            ) else 0.0
            candidate.rerank_score = base_score + trust_score + treatment_score
        return sorted(candidates, key=lambda item: item.rerank_score, reverse=True)

    def warmup(self) -> None:
        """显式启动 Reranker 子进程，并在失败时记录可观测错误状态。"""

        if self.worker is None:
            return
        try:
            self.worker.start()
        except RuntimeError as error:
            self.load_error = str(error)
            self.close()

    def _predict(
        self,
        query: str,
        candidates: list[RankedDocument],
    ) -> list[float]:
        """分批计算查询与候选证据的 Cross-Encoder 概率分数。

        Args:
            query: 用户检索文本。
            candidates: 等待精排的 RRF 候选。

        Returns:
            与候选顺序一致、经 sigmoid 映射到零到一的相关性分数。
        """

        pairs = [
            [
                query,
                candidate.document.searchable_text[: self.max_length * 8],
            ]
            for candidate in candidates
        ]
        if self.worker is None:
            return []
        return self.worker.predict(pairs)

    def close(self) -> None:
        """关闭隔离的 Reranker 进程并释放模型资源。"""

        if self.worker is not None:
            self.worker.close()
            self.worker = None
