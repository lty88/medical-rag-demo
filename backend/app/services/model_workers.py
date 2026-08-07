"""把 Torch/MPS 模型隔离到独立进程，避免 macOS 与 FAISS 的 OpenMP 冲突。"""

from __future__ import annotations

import atexit
import multiprocessing
import os
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any, Literal


WorkerResponse = tuple[Literal["ready", "ok", "error"], Any]


def _send_error(connection: Connection, error: Exception) -> None:
    """把子进程异常转换为可跨进程传递的错误文本。

    Args:
        connection: 子进程通信管道。
        error: 模型加载或推理产生的异常。
    """

    connection.send(("error", f"{type(error).__name__}: {error}"))


def _embedding_worker_main(connection: Connection, config: dict[str, Any]) -> None:
    """在纯 Torch 子进程中加载 Embedding 并响应编码命令。

    Args:
        connection: 与主进程双向通信的管道。
        config: 模型名称、设备、长度和缓存目录配置。
    """

    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    try:
        from app.services.embedding import MedicalEmbeddingEncoder

        encoder = MedicalEmbeddingEncoder(**config)
        connection.send(
            (
                "ready",
                {"dimension": encoder.dimension, "device": encoder.device},
            )
        )
    except Exception as error:
        _send_error(connection, error)
        connection.close()
        return

    while True:
        try:
            command, payload = connection.recv()
            if command == "close":
                break
            if command == "encode_queries":
                vectors = encoder.encode_queries(
                    payload["texts"],
                    batch_size=payload["batch_size"],
                )
            elif command == "encode_documents":
                vectors = encoder.encode_documents(
                    payload["texts"],
                    batch_size=payload["batch_size"],
                )
            else:
                raise ValueError(f"未知 Embedding 命令：{command}")
            connection.send(("ok", vectors))
        except EOFError:
            break
        except Exception as error:
            _send_error(connection, error)
    connection.close()


def _reranker_worker_main(connection: Connection, config: dict[str, Any]) -> None:
    """在纯 Torch 子进程中加载 Cross-Encoder 并响应精排命令。

    Args:
        connection: 与主进程双向通信的管道。
        config: 模型名称、设备、长度、批大小和缓存目录配置。
    """

    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        from app.services.embedding import resolve_model_device

        device = resolve_model_device(config["device"], torch)
        cache_dir = config.get("cache_dir")
        tokenizer = AutoTokenizer.from_pretrained(
            config["model_name"],
            cache_dir=cache_dir,
        )
        model_dtype = torch.float16 if device in {"cuda", "mps"} else torch.float32
        model = AutoModelForSequenceClassification.from_pretrained(
            config["model_name"],
            cache_dir=cache_dir,
            dtype=model_dtype,
            low_cpu_mem_usage=True,
        )
        model.to(device)
        model.eval()
        connection.send(("ready", {"device": device}))
    except Exception as error:
        _send_error(connection, error)
        connection.close()
        return

    while True:
        try:
            command, payload = connection.recv()
            if command == "close":
                break
            if command != "rerank":
                raise ValueError(f"未知 Reranker 命令：{command}")
            pairs = payload["pairs"]
            scores: list[float] = []
            for start in range(0, len(pairs), config["batch_size"]):
                encoded = tokenizer(
                    pairs[start : start + config["batch_size"]],
                    padding=True,
                    truncation=True,
                    max_length=config["max_length"],
                    return_tensors="pt",
                )
                encoded = {key: value.to(device) for key, value in encoded.items()}
                with torch.inference_mode():
                    logits = model(**encoded, return_dict=True).logits.view(-1).float()
                    scores.extend(
                        float(score) for score in torch.sigmoid(logits).cpu().tolist()
                    )
            connection.send(("ok", scores))
        except EOFError:
            break
        except Exception as error:
            _send_error(connection, error)
    connection.close()


class ModelWorkerClient:
    """管理一个使用 spawn 启动的模型子进程及请求响应协议。"""

    def __init__(
        self,
        target: Any,
        config: dict[str, Any],
        startup_timeout: float = 1_800,
        request_timeout: float = 600,
    ) -> None:
        """保存进程入口和模型配置，等待首次请求时启动。

        Args:
            target: 子进程入口函数。
            config: 传递给入口函数的可序列化配置。
            startup_timeout: 模型首次下载与加载的最长等待秒数。
            request_timeout: 单次推理的最长等待秒数。
        """

        self.target = target
        self.config = config
        self.startup_timeout = startup_timeout
        self.request_timeout = request_timeout
        self.process: multiprocessing.Process | None = None
        self.connection: Connection | None = None
        self.ready_payload: dict[str, Any] | None = None
        atexit.register(self.close)

    def start(self) -> dict[str, Any]:
        """使用 spawn 启动隔离模型进程并等待模型准备完成。

        Returns:
            子进程报告的设备、维度等就绪信息。

        Raises:
            RuntimeError: 模型加载失败、超时或子进程异常退出时抛出。
        """

        if self.ready_payload is not None:
            return self.ready_payload
        context = multiprocessing.get_context("spawn")
        parent_connection, child_connection = context.Pipe()
        self.process = context.Process(
            target=self.target,
            args=(child_connection, self.config),
            daemon=True,
        )
        self.process.start()
        child_connection.close()
        self.connection = parent_connection
        status, payload = self._receive(self.startup_timeout)
        if status != "ready":
            self.close()
            raise RuntimeError(str(payload))
        self.ready_payload = dict(payload)
        return self.ready_payload

    def request(self, command: str, payload: dict[str, Any]) -> Any:
        """向已经启动的模型进程发送一次推理请求。

        Args:
            command: 子进程支持的命令名称。
            payload: 输入文本、批大小等可序列化参数。

        Returns:
            子进程返回的向量矩阵或相关性分数。

        Raises:
            RuntimeError: 子进程返回错误或通信失败时抛出。
        """

        self.start()
        if self.connection is None:
            raise RuntimeError("模型进程通信管道不可用")
        self.connection.send((command, payload))
        status, result = self._receive(self.request_timeout)
        if status != "ok":
            raise RuntimeError(str(result))
        return result

    def _receive(self, timeout: float) -> WorkerResponse:
        """在限定时间内等待并校验子进程响应。

        Args:
            timeout: 最长等待秒数。

        Returns:
            子进程状态与负载组成的二元组。

        Raises:
            RuntimeError: 超时、管道关闭或子进程退出时抛出。
        """

        if self.connection is None or not self.connection.poll(timeout):
            raise RuntimeError(f"模型进程在 {timeout:.0f} 秒内没有响应")
        try:
            return self.connection.recv()
        except EOFError as error:
            raise RuntimeError("模型进程意外退出") from error

    def close(self) -> None:
        """关闭模型通信管道，并回收仍在运行的子进程。"""

        if self.connection is not None:
            try:
                if self.process is not None and self.process.is_alive():
                    self.connection.send(("close", {}))
            except (BrokenPipeError, EOFError, OSError):
                pass
            self.connection.close()
            self.connection = None
        if self.process is not None:
            self.process.join(timeout=5)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout=5)
            self.process = None
        self.ready_payload = None


class EmbeddingWorkerClient:
    """为主进程提供隔离的中文医疗 Embedding 编码能力。"""

    def __init__(
        self,
        model_name: str,
        device: str = "auto",
        query_max_length: int = 128,
        document_max_length: int = 256,
        cache_dir: Path | None = None,
        subfolder: str | None = None,
    ) -> None:
        """创建 Embedding 工作进程客户端但不立即加载模型。

        Args:
            model_name: Hugging Face 模型名称或本地目录。
            device: 子进程推理设备。
            query_max_length: 查询最大词元数。
            document_max_length: 文档最大词元数。
            cache_dir: 模型权重缓存目录。
            subfolder: 模型文件位于仓库内的子目录。
        """

        self.client = ModelWorkerClient(
            _embedding_worker_main,
            {
                "model_name": model_name,
                "device": device,
                "query_max_length": query_max_length,
                "document_max_length": document_max_length,
                "cache_dir": str(cache_dir) if cache_dir else None,
                "subfolder": subfolder,
            },
        )

    @property
    def dimension(self) -> int:
        """启动模型并返回 Embedding 输出维度。

        Returns:
            模型配置中的隐藏层维度。
        """

        return int(self.client.start()["dimension"])

    @property
    def device(self) -> str:
        """启动模型并返回实际推理设备。

        Returns:
            cpu、mps 或 cuda 设备名称。
        """

        return str(self.client.start()["device"])

    def encode_queries(self, texts: list[str], batch_size: int = 32) -> Any:
        """在隔离进程中批量编码用户查询。

        Args:
            texts: 待编码查询列表。
            batch_size: 单次模型推理数量。

        Returns:
            归一化 float32 查询向量矩阵。
        """

        return self.client.request(
            "encode_queries",
            {"texts": texts, "batch_size": batch_size},
        )

    def encode_documents(self, texts: list[str], batch_size: int = 32) -> Any:
        """在隔离进程中批量编码医疗知识正文。

        Args:
            texts: 待编码知识正文列表。
            batch_size: 单次模型推理数量。

        Returns:
            归一化 float32 文档向量矩阵。
        """

        return self.client.request(
            "encode_documents",
            {"texts": texts, "batch_size": batch_size},
        )

    def close(self) -> None:
        """关闭 Embedding 工作进程并释放模型资源。"""

        self.client.close()


class RerankerWorkerClient:
    """为主进程提供隔离的 Cross-Encoder 精排能力。"""

    def __init__(
        self,
        model_name: str,
        device: str = "auto",
        max_length: int = 512,
        batch_size: int = 8,
        cache_dir: Path | None = None,
    ) -> None:
        """创建 Reranker 工作进程客户端，等待预热或首次请求时启动。

        Args:
            model_name: Hugging Face Reranker 名称或本地目录。
            device: 子进程推理设备。
            max_length: 查询与候选对的最大词元数。
            batch_size: 单次精排的候选数量。
            cache_dir: 模型权重缓存目录。
        """

        self.client = ModelWorkerClient(
            _reranker_worker_main,
            {
                "model_name": model_name,
                "device": device,
                "max_length": max_length,
                "batch_size": batch_size,
                "cache_dir": str(cache_dir) if cache_dir else None,
            },
        )

    def start(self) -> dict[str, Any]:
        """启动 Reranker 子进程并等待模型加载完成。

        Returns:
            子进程实际使用的推理设备等就绪信息。
        """

        return self.client.start()

    def predict(self, pairs: list[list[str]]) -> list[float]:
        """在隔离进程中计算查询与候选对的相关性分数。

        Args:
            pairs: 每项包含查询和候选正文的二元列表。

        Returns:
            与输入顺序一致的零到一相关性分数。
        """

        return [
            float(score)
            for score in self.client.request("rerank", {"pairs": pairs})
        ]

    def close(self) -> None:
        """关闭 Reranker 工作进程并释放模型资源。"""

        self.client.close()
