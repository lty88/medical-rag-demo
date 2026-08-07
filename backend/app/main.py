"""FastAPI 应用入口。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import ConsultationRequest, ConsultationResponse, KnowledgeStats
from app.pipeline import MedicalRagPipeline


pipeline = MedicalRagPipeline(settings)


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


@app.post("/api/consult", response_model=ConsultationResponse)
def consult(request: ConsultationRequest) -> ConsultationResponse:
    """执行完整的医疗信息安全检索流程。

    Args:
        request: 症状、人群和地区信息。

    Returns:
        包含安全结论、证据和可解释处理步骤的响应。
    """

    return pipeline.consult(request)
