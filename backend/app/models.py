"""API 与检索链路的数据模型。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ConsultationRequest(BaseModel):
    """用户提交的症状与基本人群信息。"""

    symptoms: str = Field(min_length=2, max_length=2000)
    age: float = Field(ge=0, le=120)
    sex: Literal["female", "male", "other", "unknown"] = "unknown"
    pregnant: bool = False
    region: str = Field(default="CN", min_length=2, max_length=12)
    duration: str | None = Field(default=None, max_length=100)
    temperature: float | None = Field(default=None, ge=30, le=45)
    additional_info: str | None = Field(default=None, max_length=1000)

    @field_validator("pregnant")
    @classmethod
    def validate_pregnancy(cls, value: bool, info: Any) -> bool:
        """限制明显矛盾的孕期输入。

        Args:
            value: 用户选择的孕期状态。
            info: Pydantic 当前字段校验上下文。

        Returns:
            通过一致性检查的孕期状态。

        Raises:
            ValueError: 非女性用户被标记为孕期时抛出。
        """

        sex = info.data.get("sex")
        if value and sex not in {"female", "unknown"}:
            raise ValueError("孕期状态与所选性别不一致")
        return value


class SourceDocument(BaseModel):
    """统一格式的知识库文档。"""

    id: str
    title: str
    question: str = ""
    content: str
    source: str
    source_url: str | None = None
    source_type: str
    trust_level: str = "secondary"
    allow_treatment_generation: bool = False
    regions: list[str] = Field(default_factory=lambda: ["CN"])
    minimum_age: float | None = None
    maximum_age: float | None = None
    pregnancy_allowed: bool | None = None
    guideline_version: str | None = None
    updated_at: str | None = None
    license: str | None = None
    retrieval_only: bool = True
    keywords: list[str] = Field(default_factory=list)
    cautions: list[str] = Field(default_factory=list)

    @property
    def searchable_text(self) -> str:
        """拼接用于召回和精排的文档文本。

        Returns:
            包含标题、问题、正文和关键词的完整检索文本。
        """

        return " ".join(
            item
            for item in [self.title, self.question, self.content, " ".join(self.keywords)]
            if item
        )


class RankedDocument(BaseModel):
    """带各阶段分数和过滤说明的候选文档。"""

    document: SourceDocument
    bm25_score: float = 0
    vector_score: float = 0
    rrf_score: float = 0
    rerank_score: float = 0
    filter_notes: list[str] = Field(default_factory=list)


class PipelineStep(BaseModel):
    """前端可展示的处理步骤。"""

    key: str
    label: str
    status: Literal["pending", "running", "passed", "blocked", "fallback"]
    detail: str
    duration_ms: int = 0


class Citation(BaseModel):
    """答案中展示的出处。"""

    marker: str
    title: str
    source: str
    source_url: str | None
    trust_level: str
    excerpt: str
    allow_treatment_generation: bool


class AnswerSection(BaseModel):
    """结构化答案的一个内容区块。"""

    title: str
    content: str


class ConsultationResponse(BaseModel):
    """完整的安全咨询响应。"""

    request_id: str
    urgency: Literal["emergency", "urgent", "routine", "insufficient"]
    blocked: bool
    title: str
    summary: str
    sections: list[AnswerSection]
    red_flags: list[str]
    follow_up_questions: list[str]
    structured_symptoms: dict[str, Any]
    citations: list[Citation]
    pipeline: list[PipelineStep]
    validation_issues: list[str]
    retrieval_mode: str
    privacy_notice: str
    disclaimer: str


class KnowledgeStats(BaseModel):
    """知识库加载状态。"""

    total_documents: int
    keyword_document_count: int
    vector_document_count: int
    source_counts: dict[str, int]
    trust_counts: dict[str, int]
    vector_mode: str
    embedding_model: str | None
    vector_index_ready: bool
    reranker_mode: str
    reranker_model: str | None
    capped: bool
