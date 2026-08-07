"""全量中文医疗 FAISS 持久化向量索引。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.embedding_text import EMBEDDING_TEXT_VERSION
from app.services.model_workers import EmbeddingWorkerClient


class PersistentFaissIndex:
    """加载离线构建的全量 FAISS 索引并执行独立语义召回。"""

    def __init__(
        self,
        index_path: Path,
        manifest_path: Path,
        model_name: str,
        model_subfolder: str | None = None,
        device: str = "auto",
        query_max_length: int = 128,
        nprobe: int = 32,
        cache_dir: Path | None = None,
    ) -> None:
        """校验索引清单并加载 FAISS，向量模型在首次查询时加载。

        Args:
            index_path: FAISS 二进制索引路径。
            manifest_path: 与索引配套的构建清单路径。
            model_name: 查询端必须使用的向量模型名称。
            model_subfolder: 模型文件位于 Hugging Face 仓库内的子目录。
            device: 查询向量模型的推理设备。
            query_max_length: 查询编码允许的最大词元数。
            nprobe: IVF 查询时探测的倒排分区数量。
            cache_dir: Embedding 模型权重缓存目录。

        Raises:
            ValueError: 文件缺失、索引未完成或模型配置不一致时抛出。
        """

        if not index_path.is_file() or not manifest_path.is_file():
            raise ValueError("FAISS 索引或构建清单不存在")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "complete":
            raise ValueError("FAISS 索引尚未构建完成")
        if manifest.get("embedding_model") != model_name:
            raise ValueError(
                "查询模型与建库模型不一致："
                f"{model_name} != {manifest.get('embedding_model')}"
            )
        if manifest.get("embedding_model_subfolder") != model_subfolder:
            raise ValueError("查询模型子目录与建库配置不一致")
        if manifest.get("embedding_text_version") != EMBEDDING_TEXT_VERSION:
            raise ValueError("FAISS 向量文本规则版本过旧，请重新构建索引")

        try:
            import faiss
        except ImportError as error:
            raise ValueError("当前环境尚未安装 faiss-cpu") from error

        self.index_path = index_path
        self.manifest_path = manifest_path
        self.manifest: dict[str, Any] = manifest
        self.model_name = model_name
        self.model_subfolder = model_subfolder
        self.device = device
        self.query_max_length = query_max_length
        self.nprobe = nprobe
        self.cache_dir = cache_dir
        self.faiss = faiss
        self.index = faiss.read_index(str(index_path))
        if int(self.index.ntotal) != self.document_count:
            raise ValueError("FAISS 二进制文档数与构建清单不一致")
        inverted_index = faiss.extract_index_ivf(self.index)
        inverted_index.nprobe = nprobe
        self._encoder: EmbeddingWorkerClient | None = None

    @property
    def document_count(self) -> int:
        """返回向量索引覆盖的文档数量。

        Returns:
            已写入 FAISS 的全量文档数。
        """

        return int(self.manifest.get("document_count", 0))

    @property
    def mode(self) -> str:
        """返回前端可展示的向量检索实现说明。

        Returns:
            包含索引类型、模型和探测参数的模式文本。
        """

        index_type = str(self.manifest.get("index_type", "FAISS"))
        return f"{index_type} 全量独立召回 / {self.model_name} / nprobe={self.nprobe}"

    def search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        """对全量 FAISS 索引执行查询并返回 SQLite 行号。

        Args:
            query: 已脱敏的用户医疗查询。
            top_k: 最多返回的向量候选数量。

        Returns:
            按余弦近似分数降序排列的 SQLite 行号与分数。
        """

        if top_k <= 0 or not query.strip():
            return []
        encoder = self._get_encoder()
        query_matrix = encoder.encode_queries([query], batch_size=1)
        scores, rowids = self.index.search(
            query_matrix,
            min(top_k, self.document_count),
        )
        return [
            (int(rowid), float(score))
            for rowid, score in zip(rowids[0], scores[0], strict=False)
            if rowid > 0
        ]

    def _get_encoder(self) -> EmbeddingWorkerClient:
        """延迟加载查询向量模型，避免仅查看统计时占用模型内存。

        Returns:
            与离线建库模型完全一致的中文医疗向量编码器。
        """

        if self._encoder is None:
            self._encoder = EmbeddingWorkerClient(
                self.model_name,
                device=self.device,
                query_max_length=self.query_max_length,
                document_max_length=int(
                    self.manifest.get("document_max_length", 256)
                ),
                cache_dir=self.cache_dir,
                subfolder=self.model_subfolder,
            )
        return self._encoder

    def close(self) -> None:
        """关闭隔离的查询 Embedding 进程并释放模型资源。"""

        if self._encoder is not None:
            self._encoder.close()
            self._encoder = None
