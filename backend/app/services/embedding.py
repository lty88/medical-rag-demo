"""中文医疗文本向量编码服务。"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray


def resolve_model_device(requested_device: str, torch_module: Any) -> str:
    """根据显式配置和硬件能力选择模型推理设备。

    Args:
        requested_device: 用户配置的设备名称，支持 auto、mps、cuda 和 cpu。
        torch_module: 已导入的 PyTorch 模块。

    Returns:
        可直接传给 PyTorch 的设备名称。

    Raises:
        ValueError: 配置了当前机器不支持的设备时抛出。
    """

    if requested_device != "auto":
        if requested_device == "cuda" and not torch_module.cuda.is_available():
            raise ValueError("当前环境不可用 CUDA")
        if requested_device == "mps" and not torch_module.backends.mps.is_available():
            raise ValueError("当前环境不可用 Apple MPS")
        if requested_device not in {"cpu", "cuda", "mps"}:
            raise ValueError(f"不支持的模型设备：{requested_device}")
        return requested_device
    if torch_module.cuda.is_available():
        return "cuda"
    if torch_module.backends.mps.is_available():
        return "mps"
    return "cpu"


class MedicalEmbeddingEncoder:
    """使用中文医疗 BGE 模型生成归一化稠密向量。"""

    def __init__(
        self,
        model_name: str,
        device: str = "auto",
        query_max_length: int = 128,
        document_max_length: int = 256,
        cache_dir: str | Path | None = None,
        subfolder: str | None = None,
    ) -> None:
        """加载分词器和向量模型，并确定推理精度与设备。

        Args:
            model_name: Hugging Face 模型名称或本地模型目录。
            device: 推理设备，auto 会优先选择 CUDA，其次 MPS。
            query_max_length: 查询编码允许的最大词元数。
            document_max_length: 文档编码允许的最大词元数。
            cache_dir: Hugging Face 模型权重缓存目录。
            subfolder: 模型文件位于 Hugging Face 仓库内的子目录。
        """

        import torch
        from transformers import AutoModel, AutoTokenizer

        self.model_name = model_name
        self.query_max_length = query_max_length
        self.document_max_length = document_max_length
        self.torch = torch
        self.device = resolve_model_device(device, torch)
        load_options: dict[str, Any] = {"cache_dir": cache_dir}
        if subfolder:
            load_options["subfolder"] = subfolder
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, **load_options)
        model_dtype = torch.float16 if self.device in {"cuda", "mps"} else torch.float32
        self.model = AutoModel.from_pretrained(
            model_name,
            **load_options,
            dtype=model_dtype,
            low_cpu_mem_usage=True,
        )
        self.model.to(self.device)
        self.model.eval()
        self.dimension = int(self.model.config.hidden_size)

    def encode_queries(
        self,
        texts: list[str],
        batch_size: int = 32,
    ) -> NDArray[np.float32]:
        """批量编码用户查询并执行 L2 归一化。

        Args:
            texts: 待编码的用户查询列表。
            batch_size: 单次送入模型的查询数量。

        Returns:
            形状为查询数乘向量维度的 float32 矩阵。
        """

        return self._encode(texts, "query", batch_size)

    def encode_documents(
        self,
        texts: list[str],
        batch_size: int = 32,
    ) -> NDArray[np.float32]:
        """批量编码医疗知识正文并执行 L2 归一化。

        Args:
            texts: 待编码的医疗知识文本列表。
            batch_size: 单次送入模型的文档数量。

        Returns:
            形状为文档数乘向量维度的 float32 矩阵。
        """

        return self._encode(texts, "document", batch_size)

    def _encode(
        self,
        texts: list[str],
        text_kind: Literal["query", "document"],
        batch_size: int,
    ) -> NDArray[np.float32]:
        """按批执行分词、CLS 池化、归一化和 CPU 回收。

        Args:
            texts: 待编码文本列表。
            text_kind: 文本属于查询还是知识文档。
            batch_size: 单次推理的文本数量。

        Returns:
            可直接写入 FAISS 的连续 float32 向量矩阵。

        Raises:
            ValueError: 批大小不是正整数时抛出。
        """

        import numpy as np

        if batch_size <= 0:
            raise ValueError("向量编码批大小必须大于 0")
        if not texts:
            return np.empty((0, self.dimension), dtype="float32")

        max_length = (
            self.query_max_length
            if text_kind == "query"
            else self.document_max_length
        )
        batches: list[NDArray[np.float32]] = []
        for start in range(0, len(texts), batch_size):
            character_limit = max_length * 8
            batch_texts = [
                text[:character_limit]
                for text in texts[start : start + batch_size]
            ]
            encoded = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            )
            encoded = {key: value.to(self.device) for key, value in encoded.items()}
            with self.torch.inference_mode():
                output = self.model(**encoded, return_dict=True)
                vectors = self.torch.nn.functional.normalize(
                    output.last_hidden_state[:, 0],
                    p=2,
                    dim=-1,
                )
            batches.append(vectors.float().cpu().numpy())
        return np.ascontiguousarray(np.concatenate(batches, axis=0), dtype="float32")
