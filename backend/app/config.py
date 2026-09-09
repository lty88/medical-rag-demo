"""应用配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env", override=False)


def parse_cors_origins(value: str | None) -> tuple[str, ...]:
    """解析逗号分隔的前端来源并提供本地开发默认值。

    Args:
        value: 环境变量中的逗号分隔来源列表。

    Returns:
        去除空白和末尾斜杠后的允许来源元组。
    """

    default_origins = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    if not value:
        return default_origins
    origins = tuple(
        origin.strip().rstrip("/")
        for origin in value.split(",")
        if origin.strip()
    )
    return origins or default_origins


@dataclass(frozen=True)
class Settings:
    """集中保存后端运行参数。"""

    app_name: str = "中文医疗混合检索系统"
    app_version: str = "0.2.0"
    sample_data_path: Path = BASE_DIR / "data" / "sample_knowledge.jsonl"
    raw_data_dir: Path = BASE_DIR / "data" / "raw"
    search_index_path: Path = Path(
        os.getenv("SEARCH_INDEX_PATH")
        or str(BASE_DIR / "data" / "processed" / "knowledge.db")
    )
    faiss_index_path: Path = Path(
        os.getenv("FAISS_INDEX_PATH")
        or str(BASE_DIR / "data" / "processed" / "medical.faiss")
    )
    faiss_manifest_path: Path = Path(
        os.getenv("FAISS_MANIFEST_PATH")
        or str(BASE_DIR / "data" / "processed" / "medical.faiss.json")
    )
    model_cache_dir: Path = Path(
        os.getenv("MODEL_CACHE_DIR")
        or str(BASE_DIR / "data" / "models")
    )
    max_loaded_documents: int = int(os.getenv("MAX_LOADED_DOCUMENTS", "20000"))
    bm25_top_k: int = int(os.getenv("BM25_TOP_K", "100"))
    vector_top_k: int = int(os.getenv("VECTOR_TOP_K", "100"))
    rrf_top_k: int = int(os.getenv("RRF_TOP_K", "40"))
    retrieval_top_k: int = int(os.getenv("RETRIEVAL_TOP_K", "20"))
    final_top_k: int = int(os.getenv("FINAL_TOP_K", "4"))
    embedding_model: str | None = os.getenv(
        "EMBEDDING_MODEL", "ming0302/bge-m3-medical-cn"
    ) or None
    embedding_model_subfolder: str | None = os.getenv(
        "EMBEDDING_MODEL_SUBFOLDER", "model"
    ) or None
    reranker_model: str | None = os.getenv(
        "RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"
    ) or None
    model_device: str = os.getenv("MODEL_DEVICE", "auto")
    embedding_query_max_length: int = int(
        os.getenv("EMBEDDING_QUERY_MAX_LENGTH", "128")
    )
    reranker_max_length: int = int(os.getenv("RERANKER_MAX_LENGTH", "512"))
    reranker_batch_size: int = int(os.getenv("RERANKER_BATCH_SIZE", "8"))
    faiss_nprobe: int = int(os.getenv("FAISS_NPROBE", "32"))
    llm_base_url: str | None = os.getenv("LLM_BASE_URL") or None
    llm_api_key: str | None = os.getenv("LLM_API_KEY") or None
    llm_model: str | None = os.getenv("LLM_MODEL") or None
    llm_vision_model: str | None = (
        os.getenv("LLM_VISION_MODEL") or os.getenv("LLM_MODEL") or None
    )
    llm_timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "180"))
    llm_evidence_max_characters: int = int(
        os.getenv("LLM_EVIDENCE_MAX_CHARACTERS", "2500")
    )
    llm_max_output_tokens: int = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "1200"))
    llm_structured_method: str = os.getenv("LLM_STRUCTURED_METHOD", "prompt")
    medical_document_max_output_tokens: int = int(
        os.getenv("MEDICAL_DOCUMENT_MAX_OUTPUT_TOKENS", "2400")
    )
    llm_enable_thinking: bool | None = (
        os.getenv("LLM_ENABLE_THINKING", "").strip().lower()
        in {"1", "true", "yes", "on"}
        if os.getenv("LLM_ENABLE_THINKING", "").strip()
        else None
    )
    retrieval_log_top_k: int = int(os.getenv("RETRIEVAL_LOG_TOP_K", "10"))
    retrieval_log_content_characters: int = int(
        os.getenv("RETRIEVAL_LOG_CONTENT_CHARACTERS", "300")
    )
    medical_document_max_bytes: int = int(
        os.getenv("MEDICAL_DOCUMENT_MAX_BYTES", str(12 * 1024 * 1024))
    )
    medical_document_max_characters: int = int(
        os.getenv("MEDICAL_DOCUMENT_MAX_CHARACTERS", "30000")
    )
    medical_document_max_pdf_pages: int = int(
        os.getenv("MEDICAL_DOCUMENT_MAX_PDF_PAGES", "20")
    )
    cors_origins: tuple[str, ...] = parse_cors_origins(os.getenv("CORS_ORIGINS"))


settings = Settings()
