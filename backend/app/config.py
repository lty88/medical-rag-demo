"""应用配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


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
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )


settings = Settings()
