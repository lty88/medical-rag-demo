"""API 与检索链路的数据模型。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ConsultationVisualSymptom(BaseModel):
    """用户在人体图谱某个部位勾选的通俗症状。"""

    id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=100)
    query_text: str = Field(min_length=1, max_length=200)
    department_ids: list[str] = Field(default_factory=list, max_length=12)


class ConsultationVisualComplaint(BaseModel):
    """人体图谱中一个已选择部位及其症状集合。"""

    region_id: str = Field(min_length=1, max_length=100)
    region_name: str = Field(min_length=1, max_length=100)
    structure_label: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=500)
    symptoms: list[ConsultationVisualSymptom] = Field(
        default_factory=list,
        max_length=12,
    )
    department_ids: list[str] = Field(default_factory=list, max_length=12)


class ConsultationVisualContext(BaseModel):
    """健康可视化传入问诊链路的导航上下文。"""

    source: Literal["health_atlas"] = "health_atlas"
    anatomy_model: Literal["male", "female"] = "male"
    system_id: str = Field(min_length=1, max_length=64)
    system_name: str = Field(min_length=1, max_length=100)
    organ_id: str = Field(min_length=1, max_length=64)
    organ_name: str = Field(min_length=1, max_length=100)
    organ_summary: str = Field(default="", max_length=500)
    observation: str = Field(default="", max_length=500)
    complaints: list[ConsultationVisualComplaint] = Field(
        default_factory=list,
        max_length=20,
    )
    suggested_departments: list[str] = Field(default_factory=list, max_length=20)


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
    visual_context: ConsultationVisualContext | None = None

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
    generation_mode: Literal["configured-llm", "evidence-template", "not-run"]
    generation_model: str | None
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
    llm_ready: bool
    llm_model: str | None
    capped: bool


class ResearchSearchRequest(BaseModel):
    """研究工作台提交的独立证据检索条件。"""

    query: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=8, ge=1, le=20)


class ResearchEvidence(BaseModel):
    """面向研究人员展示的单条混合检索证据。"""

    id: str
    title: str
    question: str
    excerpt: str
    source: str
    source_type: str
    trust_level: str
    source_url: str | None
    allow_treatment_generation: bool
    bm25_score: float
    vector_score: float
    rrf_score: float
    rerank_score: float


class ResearchSearchResponse(BaseModel):
    """独立证据检索、混排与精排的完整响应。"""

    request_id: str
    query: str
    total: int
    results: list[ResearchEvidence]
    retrieval_mode: str
    duration_ms: int


class MedicalDocumentFinding(BaseModel):
    """病历或检查报告中一项可追溯的关键发现。"""

    name: str = Field(min_length=1, max_length=120)
    original_text: str = Field(default="", max_length=1000)
    explanation: str = Field(min_length=1, max_length=2000)
    level: Literal["normal", "attention", "urgent", "uncertain"] = "uncertain"


class MedicalDocumentEvidence(BaseModel):
    """病历解读过程中用于辅助解释的一条本地检索证据。"""

    marker: str
    title: str
    excerpt: str
    source: str
    source_type: str
    trust_level: str
    source_url: str | None


class MedicalDocumentInterpretationResponse(BaseModel):
    """上传病历或检查报告后的结构化辅助解读结果。"""

    request_id: str
    file_name: str
    document_type: str
    extraction_mode: Literal["text", "vision"]
    title: str
    summary: str
    urgency: Literal["routine", "attention", "urgent", "insufficient"]
    findings: list[MedicalDocumentFinding]
    sections: list[AnswerSection]
    red_flags: list[str]
    questions_for_doctor: list[str]
    limitations: list[str]
    evidence: list[MedicalDocumentEvidence]
    retrieval_mode: str
    generation_model: str
    privacy_notice: str
    disclaimer: str
    duration_ms: int


class AtlasSymptomOption(BaseModel):
    """身体部位可供普通用户勾选的通俗症状表现。"""

    id: str
    label: str
    query_text: str
    department_ids: list[str] = Field(default_factory=list)


class AtlasOrgan(BaseModel):
    """健康可视化中的器官或结构说明。"""

    id: str
    name: str
    summary: str
    observation: str
    mesh_aliases: list[str] = Field(default_factory=list)
    symptom_options: list[AtlasSymptomOption] = Field(default_factory=list)
    available_models: list[Literal["male", "female"]] = Field(
        default_factory=lambda: ["male", "female"]
    )
    department_ids: list[str] = Field(default_factory=list)


class AtlasBodyRegion(BaseModel):
    """可由三维体表模型点击定位的细分身体区域。"""

    id: str
    name: str
    english_name: str
    group: str
    side: Literal["left", "right", "middle", "bilateral"]
    system_id: str = "regional"
    location: str
    summary: str
    mesh_aliases: list[str]
    symptom_options: list[AtlasSymptomOption]
    department_ids: list[str] = Field(default_factory=list)


class AtlasDepartment(BaseModel):
    """面向普通用户的医院初诊科室导航数据。"""

    id: str
    official_code: str
    name: str
    english_name: str
    group: str
    summary: str
    common_reasons: list[str]
    target_system_id: str
    target_organ_id: str | None = None
    focus_aliases: list[str] = Field(default_factory=list)
    preferred_model: Literal["male", "female"] | None = None


class AtlasSystem(BaseModel):
    """健康可视化中的人体系统说明。"""

    id: str
    name: str
    english_name: str
    color: str
    summary: str
    organs: list[AtlasOrgan]
    available_models: list[Literal["male", "female"]] = Field(
        default_factory=lambda: ["male", "female"]
    )


class AtlasModelProfile(BaseModel):
    """健康可视化可切换的解剖模型及其医学覆盖范围。"""

    id: Literal["male", "female"]
    name: str
    english_name: str
    description: str
    coverage: str
    structure_count: int
    available_system_ids: list[str]


class BodyAtlasResponse(BaseModel):
    """人体系统认知页面使用的医学科普数据。"""

    title: str
    description: str
    systems: list[AtlasSystem]
    departments: list[AtlasDepartment]
    body_regions: list[AtlasBodyRegion]
    models: list[AtlasModelProfile]
    default_model: Literal["male", "female"] = "male"
    disclaimer: str
