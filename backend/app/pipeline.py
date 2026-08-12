"""串联隐私、分诊、检索、生成与校验的主流程。"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from app.config import Settings
from app.models import (
    AnswerSection,
    ConsultationRequest,
    ConsultationResponse,
    KnowledgeStats,
    PipelineStep,
    RankedDocument,
    SourceDocument,
)
from app.services.corpus import build_stats, load_documents
from app.services.faiss_index import PersistentFaissIndex
from app.services.filters import filter_candidates
from app.services.generator import EvidenceBoundGenerator, GeneratedAnswer
from app.services.persistent_index import PersistentBM25Index
from app.services.privacy import PrivacyResult, redact_privacy
from app.services.reranker import MedicalReranker, is_treatment_intent
from app.services.retrieval import BM25Retriever, reciprocal_rank_fusion
from app.services.symptoms import structure_symptoms
from app.services.triage import evaluate_red_flags
from app.services.validator import validate_answer


DISCLAIMER = (
    "本系统用于医疗信息辅助检索与技术研究，不提供诊断、处方，也不能替代医生。"
)
LOGGER = logging.getLogger("uvicorn.error.medical_rag.pipeline")


class MedicalRagPipeline:
    """全量中文医疗混合检索与可解释安全流水线。"""

    def __init__(self, settings: Settings) -> None:
        """加载知识库并初始化两路召回、精排和生成服务。

        Args:
            settings: 应用运行配置。
        """

        self.settings = settings
        self.persistent_index: PersistentBM25Index | None = None
        self.faiss_index: PersistentFaissIndex | None = None
        self.vector_load_error: str | None = None
        if settings.search_index_path.is_file():
            try:
                self.persistent_index = PersistentBM25Index(settings.search_index_path)
            except (ValueError, OSError):
                self.persistent_index = None

        if self.persistent_index is not None:
            self.documents = []
            self.capped = False
            self.bm25 = None
            if settings.embedding_model:
                try:
                    self.faiss_index = PersistentFaissIndex(
                        settings.faiss_index_path,
                        settings.faiss_manifest_path,
                        settings.embedding_model,
                        model_subfolder=settings.embedding_model_subfolder,
                        device=settings.model_device,
                        query_max_length=settings.embedding_query_max_length,
                        nprobe=settings.faiss_nprobe,
                        cache_dir=settings.model_cache_dir,
                    )
                    if (
                        self.faiss_index.document_count
                        != self.persistent_index.document_count
                    ):
                        raise ValueError("FAISS 与 SQLite 的全量文档数不一致")
                except (ImportError, OSError, RuntimeError, ValueError) as error:
                    self.faiss_index = None
                    self.vector_load_error = str(error)
        else:
            self.documents, self.capped = load_documents(
                settings.sample_data_path,
                settings.raw_data_dir,
                settings.max_loaded_documents,
            )
            self.bm25 = BM25Retriever(self.documents)
        self.reranker = MedicalReranker(
            settings.reranker_model,
            device=settings.model_device,
            max_length=settings.reranker_max_length,
            batch_size=settings.reranker_batch_size,
            cache_dir=settings.model_cache_dir,
        )
        self.generator = EvidenceBoundGenerator(
            settings.llm_base_url,
            settings.llm_api_key,
            settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            evidence_max_characters=settings.llm_evidence_max_characters,
            max_output_tokens=settings.llm_max_output_tokens,
            enable_thinking=settings.llm_enable_thinking,
        )

    def stats(self) -> KnowledgeStats:
        """返回当前知识库和可选模型的加载状态。

        Returns:
            知识文档数量、来源分布和检索实现说明。
        """

        if self.persistent_index is not None:
            vector_count = (
                self.faiss_index.document_count if self.faiss_index is not None else 0
            )
            vector_mode = (
                self.faiss_index.mode
                if self.faiss_index is not None
                else f"FAISS 全量索引未就绪：{self.vector_load_error or '文件不存在'}"
            )
            return KnowledgeStats(
                total_documents=self.persistent_index.document_count,
                keyword_document_count=self.persistent_index.document_count,
                vector_document_count=vector_count,
                source_counts=self.persistent_index.source_counts(),
                trust_counts=self.persistent_index.trust_counts(),
                vector_mode=vector_mode,
                embedding_model=self.settings.embedding_model,
                vector_index_ready=self.faiss_index is not None,
                reranker_mode=self.reranker.mode,
                reranker_model=self.settings.reranker_model,
                llm_ready=all(
                    (
                        self.settings.llm_base_url,
                        self.settings.llm_api_key,
                        self.settings.llm_model,
                    )
                ),
                llm_model=self.settings.llm_model,
                capped=False,
            )
        return build_stats(
            self.documents,
            "FAISS 全量索引未就绪；非持久化模式仅使用 BM25",
            self.reranker.mode,
            self.capped,
            self.settings.embedding_model,
            self.settings.reranker_model,
            all(
                (
                    self.settings.llm_base_url,
                    self.settings.llm_api_key,
                    self.settings.llm_model,
                )
            ),
            self.settings.llm_model,
        )

    def close(self) -> None:
        """关闭数据库连接及隔离的 Embedding、Reranker 模型进程。"""

        if self.faiss_index is not None:
            self.faiss_index.close()
        if self.persistent_index is not None:
            self.persistent_index.close()
        self.reranker.close()

    def warmup_models(self) -> None:
        """在服务启动阶段预热真实 Reranker，避免首次请求才下载模型。"""

        self.reranker.warmup()

    def _run_stage(
        self,
        steps: list[PipelineStep],
        key: str,
        label: str,
        detail_builder: Callable[[Any], str],
        operation: Callable[[], Any],
        success_status: str = "passed",
    ) -> Any:
        """执行一个同步阶段并记录耗时与解释文本。

        Args:
            steps: 当前响应的流水线步骤列表。
            key: 阶段稳定标识。
            label: 前端展示名称。
            detail_builder: 根据阶段结果生成说明的函数。
            operation: 实际执行的无参函数。
            success_status: 成功后的步骤状态。

        Returns:
            阶段操作的原始结果。
        """

        started_at = time.perf_counter()
        result = operation()
        duration_ms = round((time.perf_counter() - started_at) * 1000)
        steps.append(
            PipelineStep(
                key=key,
                label=label,
                status=success_status,  # type: ignore[arg-type]
                detail=detail_builder(result),
                duration_ms=duration_ms,
            )
        )
        return result

    def _log_user_input(
        self,
        request_id: str,
        request: ConsultationRequest,
        privacy: PrivacyResult,
    ) -> None:
        """记录完成隐私处理后的用户输入和基础人群信息。

        Args:
            request_id: 当前咨询请求标识。
            request: 已通过字段校验的咨询请求。
            privacy: 已完成直接身份信息脱敏的文本结果。
        """

        LOGGER.info(
            "[用户输入] %s",
            json.dumps(
                {
                    "request_id": request_id,
                    "symptoms": privacy.text,
                    "age": request.age,
                    "sex": request.sex,
                    "pregnant": request.pregnant,
                    "region": request.region,
                    "duration": request.duration,
                    "temperature": request.temperature,
                    "redacted_types": list(privacy.redacted_types),
                },
                ensure_ascii=False,
            ),
        )

    def _log_retrieval_results(
        self,
        request_id: str,
        stage: str,
        candidates: list[tuple[SourceDocument, float]] | list[RankedDocument],
    ) -> None:
        """记录某个召回或排序阶段的前若干条候选及各项分数。

        Args:
            request_id: 当前咨询请求标识。
            stage: BM25、FAISS、RRF、Reranker 或最终证据等阶段名称。
            candidates: 原始召回元组或包含多阶段分数的排序文档。
        """

        logged_candidates: list[dict[str, Any]] = []
        for rank, item in enumerate(
            candidates[: self.settings.retrieval_log_top_k], start=1
        ):
            if isinstance(item, RankedDocument):
                document = item.document
                scores = {
                    "bm25_score": round(item.bm25_score, 6),
                    "vector_score": round(item.vector_score, 6),
                    "rrf_score": round(item.rrf_score, 6),
                    "rerank_score": round(item.rerank_score, 6),
                }
            else:
                document, score = item
                scores = {"score": round(score, 6)}
            logged_candidates.append(
                {
                    "rank": rank,
                    "id": document.id,
                    "title": document.title,
                    "question": document.question,
                    "source": document.source,
                    "content_preview": document.content[
                        : self.settings.retrieval_log_content_characters
                    ],
                    **scores,
                }
            )
        LOGGER.info(
            "[检索结果][%s] %s",
            stage,
            json.dumps(
                {
                    "request_id": request_id,
                    "total": len(candidates),
                    "logged": len(logged_candidates),
                    "candidates": logged_candidates,
                },
                ensure_ascii=False,
            ),
        )

    def consult(self, request: ConsultationRequest) -> ConsultationResponse:
        """执行完整咨询链路，并在危险或校验失败时安全中止。

        Args:
            request: 已完成 API 字段校验的症状与人群信息。

        Returns:
            包含结构化答案、引用、追问和各阶段状态的响应。
        """

        request_id = uuid.uuid4().hex[:12]
        steps: list[PipelineStep] = []
        raw_text = "\n".join(
            item for item in [request.symptoms, request.additional_info] if item
        )
        privacy: PrivacyResult = self._run_stage(
            steps,
            "privacy",
            "隐私信息处理",
            lambda result: (
                f"已脱敏：{'、'.join(result.redacted_types)}"
                if result.redacted_types
                else "未发现常见直接身份信息"
            ),
            lambda: redact_privacy(raw_text),
        )
        self._log_user_input(request_id, request, privacy)
        red_flags: list[str] = self._run_stage(
            steps,
            "triage",
            "急症危险信号规则",
            lambda result: f"命中 {len(result)} 条危险信号" if result else "规则未命中",
            lambda: evaluate_red_flags(request, privacy.text),
        )

        if red_flags:
            steps[-1].status = "blocked"
            emergency_action = (
                "请立即拨打 120 或前往最近急诊，并由身边的人陪同。"
                if request.region.upper() == "CN"
                else "请立即联系所在地急救服务或前往最近急诊，并由身边的人陪同。"
            )
            return ConsultationResponse(
                request_id=request_id,
                urgency="emergency",
                blocked=True,
                title="发现需立即处理的危险信号",
                summary=f"{emergency_action}系统已停止检索和自动治疗建议。",
                sections=[
                    AnswerSection(
                        title="现在该做什么",
                        content="不要独自驾车；保持电话畅通，准备身份信息、用药清单和大致起病时间。",
                    ),
                    AnswerSection(
                        title="命中的规则",
                        content="；".join(red_flags),
                    ),
                ],
                red_flags=red_flags,
                follow_up_questions=[],
                structured_symptoms={},
                citations=[],
                pipeline=steps,
                validation_issues=[],
                retrieval_mode="stopped-before-retrieval",
                generation_mode="not-run",
                generation_model=self.settings.llm_model,
                privacy_notice="后续处理仅使用脱敏文本。",
                disclaimer=DISCLAIMER,
            )

        structured = self._run_stage(
            steps,
            "structure",
            "症状结构化与追问",
            lambda result: (
                f"识别 {len(result['symptoms'])} 个症状词，生成 {len(result['missing'])} 个追问"
            ),
            lambda: structure_symptoms(request, privacy.text),
        )
        follow_up_questions = structured["missing"]
        retrieval_query = privacy.text
        if self.persistent_index is not None:
            bm25_matches = self._run_stage(
                steps,
                "bm25",
                "全量关键词检索 SQLite FTS5 / BM25",
                lambda result: (
                    f"从 {self.persistent_index.document_count:,} 条中召回 {len(result)} 条候选"
                ),
                lambda: self.persistent_index.search(
                    retrieval_query,
                    self.settings.bm25_top_k,
                ),
            )
            if self.faiss_index is not None:
                vector_row_matches = self._run_stage(
                    steps,
                    "vector",
                    "全量中文医疗 Embedding / FAISS 独立召回",
                    lambda result: (
                        f"以 {self.faiss_index.mode} 从 "
                        f"{self.faiss_index.document_count:,} 条中独立召回 {len(result)} 条"
                    ),
                    lambda: self.faiss_index.search(
                        retrieval_query,
                        self.settings.vector_top_k,
                    ),
                )
                documents_by_rowid = self.persistent_index.get_by_rowids(
                    [rowid for rowid, _ in vector_row_matches]
                )
                vector_matches = [
                    (documents_by_rowid[rowid], score)
                    for rowid, score in vector_row_matches
                    if rowid in documents_by_rowid
                ]
                active_vector_mode = self.faiss_index.mode
            else:
                vector_matches = self._run_stage(
                    steps,
                    "vector",
                    "全量中文医疗 Embedding / FAISS 独立召回",
                    lambda result: (
                        "FAISS 全量索引未就绪，本次仅保留 BM25；"
                        f"原因：{self.vector_load_error or '索引文件不存在'}"
                    ),
                    lambda: [],
                    "fallback",
                )
                active_vector_mode = "FAISS 全量索引未就绪"
            retrieval_prefix = "SQLite FTS5/BM25 全量独立召回"
        else:
            assert self.bm25 is not None
            bm25_index_matches = self._run_stage(
                steps,
                "bm25",
                "关键词检索 BM25",
                lambda result: f"从内存语料召回 {len(result)} 条候选",
                lambda: self.bm25.search(
                    retrieval_query,
                    self.settings.retrieval_top_k,
                ),
            )
            bm25_matches = [
                (self.documents[index], score)
                for index, score in bm25_index_matches
            ]
            vector_matches = self._run_stage(
                steps,
                "vector",
                "全量中文医疗 Embedding / FAISS 独立召回",
                lambda result: (
                    "完整 SQLite/FAISS 索引未就绪，本次仅执行内存 BM25"
                ),
                lambda: [],
                "fallback",
            )
            retrieval_prefix = "内存 BM25"
            active_vector_mode = "FAISS 未就绪"
        self._log_retrieval_results(request_id, "BM25", bm25_matches)
        self._log_retrieval_results(request_id, "FAISS", vector_matches)
        mixed = self._run_stage(
            steps,
            "rrf",
            "RRF 混合排序",
            lambda result: f"合并为 {len(result)} 条去重候选",
            lambda: reciprocal_rank_fusion(
                bm25_matches,
                vector_matches,
                self.settings.rrf_top_k,
            ),
        )
        self._log_retrieval_results(request_id, "RRF", mixed)
        reranked = self._run_stage(
            steps,
            "reranker",
            "医疗 Reranker 精排",
            lambda result: f"以 {self.reranker.mode} 完成 {len(result)} 条精排",
            lambda: self.reranker.rerank(retrieval_query, mixed),
            "passed" if self.reranker.neural_available else "fallback",
        )
        if not self.reranker.neural_available:
            steps[-1].status = "fallback"
        self._log_retrieval_results(request_id, "Reranker", reranked)
        filtered, filter_reasons = self._run_stage(
            steps,
            "filters",
            "年龄、孕期、地区与版本过滤",
            lambda result: f"保留 {len(result[0])} 条，排除 {len(result[1])} 项不兼容条件",
            lambda: filter_candidates(request, reranked),
        )
        final_candidates = filtered[: self.settings.final_top_k]
        self._log_retrieval_results(request_id, "最终证据", final_candidates)
        treatment_intent = is_treatment_intent(privacy.text)
        generated: GeneratedAnswer = self._run_stage(
            steps,
            "generation",
            "结构化答案生成",
            lambda result: f"生成模式：{result.mode}；{result.detail}",
            lambda: self.generator.generate(
                privacy.text,
                final_candidates,
                follow_up_questions,
                treatment_intent,
                request_id=request_id,
            ),
            "passed",
        )
        if generated.mode != "configured-llm":
            steps[-1].status = "fallback"
        validation_issues: list[str] = self._run_stage(
            steps,
            "validation",
            "引用、禁忌、数字与幻觉校验",
            lambda result: f"发现 {len(result)} 个阻断问题" if result else "全部校验通过",
            lambda: validate_answer(generated, final_candidates, treatment_intent),
        )

        no_evidence = not final_candidates
        blocked = bool(validation_issues) or no_evidence
        if blocked:
            steps[-1].status = "blocked"
            reasons = validation_issues or ["没有找到与人群条件匹配的证据"]
            title = "当前无法给出该判断"
            summary = "安全校验未通过，系统已拒绝继续生成治疗或诊断建议。"
            sections = [
                AnswerSection(title="拒绝原因", content="；".join(reasons)),
                AnswerSection(
                    title="下一步",
                    content=(
                        "请向合格医疗专业人员提供完整症状、病史和正在使用的药物；"
                        "若症状加重或出现危险信号，请及时就医。"
                    ),
                ),
            ]
        else:
            title = generated.title
            summary = generated.summary
            sections = generated.sections

        if filter_reasons:
            structured["filter_notes"] = filter_reasons[:5]
        return ConsultationResponse(
            request_id=request_id,
            urgency="insufficient" if blocked else "routine",
            blocked=blocked,
            title=title,
            summary=summary,
            sections=sections,
            red_flags=[],
            follow_up_questions=follow_up_questions,
            structured_symptoms=structured,
            citations=generated.citations,
            pipeline=steps,
            validation_issues=validation_issues,
            retrieval_mode=(
                f"{retrieval_prefix} + {active_vector_mode} + RRF + {self.reranker.mode}"
            ),
            generation_mode=generated.mode,
            generation_model=(
                self.settings.llm_model
                if generated.mode == "configured-llm"
                else None
            ),
            privacy_notice=(
                f"已移除：{'、'.join(privacy.redacted_types)}。"
                if privacy.redacted_types
                else "未发现常见直接身份信息；后续仍仅处理本次输入。"
            ),
            disclaimer=DISCLAIMER,
        )
