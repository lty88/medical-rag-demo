"""LangGraph 请求级状态；不挂载 checkpointer，不持久化患者输入。"""

from typing import Any, TypedDict

from app.models import ConsultationRequest, ConsultationResponse, PipelineStep, RankedDocument, SourceDocument
from app.services.generator import GeneratedAnswer
from app.services.privacy import PrivacyResult


class ConsultationState(TypedDict, total=False):
    """显式声明每个节点交换的数据及最终兼容响应。"""

    request: ConsultationRequest
    request_id: str
    steps: list[PipelineStep]
    privacy: PrivacyResult
    red_flags: list[str]
    structured: dict[str, Any]
    follow_up_questions: list[str]
    retrieval_query: str
    bm25_matches: list[tuple[SourceDocument, float]]
    vector_matches: list[tuple[SourceDocument, float]]
    retrieval_prefix: str
    active_vector_mode: str
    mixed: list[RankedDocument]
    reranked: list[RankedDocument]
    final_candidates: list[RankedDocument]
    filter_reasons: list[str]
    treatment_intent: bool
    generated: GeneratedAnswer
    validation_issues: list[str]
    response: ConsultationResponse
