"""FastAPI 应用入口。"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.models import (
    BodyAtlasResponse,
    ConsultationRequest,
    ConsultationResponse,
    KnowledgeStats,
    MedicalDocumentInterpretationResponse,
    ResearchSearchRequest,
    ResearchSearchResponse,
)
from app.pipeline import MedicalRagPipeline
from app.services.atlas import build_body_atlas
from app.services.document_graph import MedicalDocumentGraph
from app.services.document_interpreter import (
    DocumentInterpretationError,
    MedicalDocumentInterpreter,
    create_document_request_id,
)


pipeline = MedicalRagPipeline(settings)
document_interpreter = MedicalDocumentInterpreter(settings)
document_graph = MedicalDocumentGraph(document_interpreter, pipeline.search_research_evidence)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """在应用生命周期内预热并最终关闭隔离模型与数据库连接。

    Args:
        _: 当前 FastAPI 应用实例，本流程不需要直接访问。

    Yields:
        模型预热完成后把控制权交给 FastAPI 请求处理阶段。
    """

    pipeline.warmup_models()
    try:
        yield
    finally:
        pipeline.close()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="危险信号优先、全量混合检索、证据过滤和生成后校验的医疗 RAG 系统。",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    """返回服务存活状态和版本。

    Returns:
        包含状态与应用版本的简单字典。
    """

    return {"status": "ok", "version": settings.app_version}


@app.get("/api/knowledge/stats", response_model=KnowledgeStats)
def knowledge_stats() -> KnowledgeStats:
    """返回当前加载的知识库统计。

    Returns:
        来源分布、可信等级和检索模式等统计。
    """

    return pipeline.stats()


@app.get("/api/atlas/body", response_model=BodyAtlasResponse)
def body_atlas() -> BodyAtlasResponse:
    """返回健康可视化页面的人体系统科普图谱。

    Returns:
        人体系统、器官说明和非诊断边界。
    """

    return build_body_atlas()


@app.post("/api/research/search", response_model=ResearchSearchResponse)
def research_search(request: ResearchSearchRequest) -> ResearchSearchResponse:
    """执行不经过 LLM 生成的可解释医疗证据检索。

    Args:
        request: 检索问题和希望返回的证据数量。

    Returns:
        BM25、FAISS、RRF 与 Reranker 精排后的证据列表。
    """

    return pipeline.search_research_evidence(request)


@app.post(
    "/api/documents/interpret",
    response_model=MedicalDocumentInterpretationResponse,
)
async def interpret_medical_document(
    file: UploadFile = File(...),
    document_type: Literal[
        "outpatient_record",
        "discharge_record",
        "laboratory_report",
        "ultrasound_report",
        "imaging_report",
        "pathology_report",
        "other",
    ] = Form(...),
    symptom_description: str = Form(default="", max_length=2000),
    interpretation_focus: str = Form(default="", max_length=300),
    sensitive_data_consent: bool = Form(...),
) -> MedicalDocumentInterpretationResponse:
    """提取单份医疗资料并通过 LangGraph 执行本地检索和模型解读。

    Args:
        file: PDF、文本或报告截图，文件只在本次请求内存中处理。
        document_type: 用户选择的病历或检查报告类型。
        symptom_description: 用户选填的症状、持续时间和就诊背景。
        interpretation_focus: 用户最希望了解的报告内容。
        sensitive_data_consent: 用户是否单独同意处理敏感医疗信息。

    Returns:
        关键发现、通俗解释、风险提示、就医提问和本地证据。

    Raises:
        HTTPException: 未同意敏感信息处理、文件超限或模型服务失败时抛出。
    """

    if not sensitive_data_consent:
        raise HTTPException(
            status_code=400,
            detail="医疗资料属于敏感个人信息，请阅读说明并主动勾选同意后再提交。",
        )
    started_at = time.perf_counter()
    request_id = create_document_request_id()
    try:
        data = await file.read(settings.medical_document_max_bytes + 1)
        document = await run_in_threadpool(
            document_interpreter.extract,
            file.filename or "未命名资料",
            data,
            document_type,
            request_id,
        )
        return await run_in_threadpool(
            document_graph.run,
            {"document": document, "symptoms": symptom_description,
             "focus": interpretation_focus, "request_id": request_id,
             "started_at": started_at},
        )
    except DocumentInterpretationError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error
    finally:
        await file.close()


@app.post("/api/consult", response_model=ConsultationResponse)
def consult(request: ConsultationRequest) -> ConsultationResponse:
    """执行完整的医疗信息安全检索流程。

    Args:
        request: 症状、人群和地区信息。

    Returns:
        包含安全结论、证据和可解释处理步骤的响应。
    """

    return pipeline.consult(request)
