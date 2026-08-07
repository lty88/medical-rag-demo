#!/usr/bin/env python3
"""以流式方式拉取并规范化 Huatuo 中文医疗问答数据。"""

from __future__ import annotations

import argparse  # 用于解析命令行参数
import gzip  # 用于压缩 JSONL.GZ 文件
import json  # 用于解析 JSON 字符串为 Python 对象
import sys  # 用于访问命令行参数和标准输入输出
import time  # 用于记录时间戳
from dataclasses import asdict, dataclass  # 用于定义数据类
from datetime import datetime, timezone  # 用于处理日期时间
from pathlib import Path  # 用于处理文件路径
from typing import Any, Iterable, Iterator  # 用于类型提示
from urllib.error import HTTPError, URLError  # 用于处理 HTTP 错误和 URL 错误   
from urllib.request import Request, urlopen  # 用于发送 HTTP 请求和接收响应

# 定义数据源的类
@dataclass(frozen=True)
class DatasetSource:
    """描述一个可下载的数据源及其安全元数据。"""

    key: str  # 数据源的唯一标识符
    repo_id: str  # 数据源的 HuggingFace 仓库 ID
    source_name: str  # 数据源的名称，用于在日志中引用
    id_prefix: str  # 用于生成唯一 ID 的前缀
    direct_train_url: str | None  # 直接训练数据的 URL，用于直接下载训练数据
    trust_level: str = "secondary"  # 数据源的信任等级，默认 "secondary"
    allow_treatment_generation: bool = False  # 是否允许生成治疗建议，默认 False

# 定义数据源的映射，将数据源的唯一标识符映射到数据源对象
SOURCES: dict[str, DatasetSource] = {
    "knowledge_graph": DatasetSource(
        key="knowledge_graph",
        repo_id="FreedomIntelligence/huatuo_knowledge_graph_qa",
        source_name="huatuo_knowledge_graph_qa",
        id_prefix="huatuo-kg",
        direct_train_url=(
            "https://huggingface.co/datasets/"
            "FreedomIntelligence/huatuo_knowledge_graph_qa/resolve/main/"
            "train_datasets.jsonl"
        ),
    ),
    "encyclopedia": DatasetSource(
        key="encyclopedia",
        repo_id="FreedomIntelligence/huatuo_encyclopedia_qa",
        source_name="huatuo_encyclopedia_qa",
        id_prefix="huatuo-encyclopedia",
        direct_train_url=(
            "https://huggingface.co/datasets/"
            "FreedomIntelligence/huatuo_encyclopedia_qa/resolve/main/"
            "train_datasets.jsonl"
        ),
    ),
    "lite": DatasetSource(
        key="lite",
        repo_id="FreedomIntelligence/Huatuo26M-Lite",
        source_name="Huatuo26M-Lite",
        id_prefix="huatuo-lite",
        direct_train_url=None,
    ),
}

# 定义解析命令行参数的函数
def parse_args() -> argparse.Namespace:
    """解析命令行参数。

    Returns:
        包含数据源、限量、分片和输出目录等配置的参数对象。
    """

    parser = argparse.ArgumentParser(
        description="流式拉取 Huatuo 数据并导出为可检索的分片 JSONL.GZ。"
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=sorted(SOURCES),
        default=["knowledge_graph", "encyclopedia"],
        help="要拉取的数据源，默认拉取知识图谱和医疗百科。",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "raw",
        help="分片与清单的输出目录。",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1_000,
        help="每个数据源最多导出的问答数；0 表示不限制。",
    )
    parser.add_argument(
        "--shard-size",
        type=int,
        default=50_000,
        help="每个 gzip 分片包含的最大记录数。",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="单次网络连接超时秒数。",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="根据清单跳过已导出的源数据位置。",
    )
    return parser.parse_args()


def utc_now() -> str:
    """生成带时区的 UTC 时间文本。

    Returns:
        ISO 8601 格式的 UTC 时间。
    """

    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: Any) -> str:
    """把数据集中的字符串或字符串列表规范成单段文本。

    Args:
        value: 原始问题或答案字段。

    Returns:
        去除空项并以换行连接后的文本。
    """

    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def normalize_row(
    row: dict[str, Any], source: DatasetSource, source_index: int
) -> dict[str, Any] | None:
    """把 Huatuo 的不同字段格式转换为统一知识记录。

    Args:
        row: 数据集原始行。
        source: 当前数据源定义。
        source_index: 当前行在远端数据源中的位置。

    Returns:
        可写入 JSONL 的统一记录；问题或答案为空时返回空值。
    """

    question = normalize_text(
        row.get("questions") or row.get("question") or row.get("instruction")
    )
    answer = normalize_text(
        row.get("answers") or row.get("answer") or row.get("output")
    )
    if not question or not answer:
        return None

    return {
        "id": f"{source.id_prefix}-{source_index}",
        "title": question[:80],
        "question": question,
        "content": answer,
        "source": source.source_name,
        "source_url": f"https://huggingface.co/datasets/{source.repo_id}",
        "source_type": "medical_qa",
        "trust_level": source.trust_level,
        "allow_treatment_generation": source.allow_treatment_generation,
        "regions": ["CN"],
        "minimum_age": None,
        "maximum_age": None,
        "pregnancy_allowed": None,
        "guideline_version": None,
        "updated_at": None,
        "license": "Apache-2.0",
        "retrieval_only": True,
        "source_row_index": source_index,
        "ingested_at": utc_now(),
    }


def iter_remote_jsonl(
    url: str, timeout: int, start_offset: int = 0
) -> Iterator[tuple[int, dict[str, Any]]]:
    """直接从远端 JSONL 文件逐行读取数据，避免完整下载到内存。

    Args:
        url: Hugging Face 原始 JSONL 文件地址。
        timeout: 网络连接超时秒数。
        start_offset: 恢复任务时要跳过的远端行数。

    Yields:
        远端行号和解析后的字典。
    """

    request = Request(url, headers={"User-Agent": "medical-rag-retrieval/0.2"})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310
        for index, raw_line in enumerate(response):
            if index < start_offset:
                continue
            line = raw_line.decode("utf-8").strip()
            if not line:
                continue
            yield index, json.loads(line)


def iter_huggingface_dataset(
    source: DatasetSource, start_offset: int = 0
) -> Iterator[tuple[int, dict[str, Any]]]:
    """通过 datasets 库流式读取没有固定原始地址的数据源。

    Args:
        source: 当前数据源定义。
        start_offset: 恢复任务时要跳过的远端行数。

    Yields:
        远端行号和数据字典。

    Raises:
        RuntimeError: 本机未安装 datasets 时抛出并提示安装方式。
    """

    try:
        from datasets import load_dataset
    except ImportError as error:
        raise RuntimeError(
            f"数据源 {source.key} 需要 datasets，请先安装 backend/requirements-data.txt"
        ) from error

    dataset: Iterable[dict[str, Any]] = load_dataset(
        source.repo_id,
        split="train",
        streaming=True,
    )
    for index, row in enumerate(dataset):
        if index < start_offset:
            continue
        yield index, row


def read_manifest(path: Path) -> dict[str, Any]:
    """读取已有下载清单。

    Args:
        path: 清单文件路径。

    Returns:
        已有清单内容；文件不存在时返回初始化结构。
    """

    if not path.exists():
        return {"version": 1, "updated_at": utc_now(), "sources": {}}
    with path.open("r", encoding="utf-8") as manifest_file:
        return json.load(manifest_file)


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    """原子写入下载清单，降低任务中断导致清单损坏的概率。

    Args:
        path: 清单文件路径。
        manifest: 要持久化的下载状态。
    """

    temporary_path = path.with_suffix(".tmp")
    with temporary_path.open("w", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file, ensure_ascii=False, indent=2)
        manifest_file.write("\n")
    temporary_path.replace(path)


class ShardWriter:
    """按指定条数把统一记录写成多个 gzip JSONL 分片。"""

    def __init__(
        self, output_dir: Path, source: DatasetSource, shard_size: int, start_shard: int
    ) -> None:
        """初始化分片写入器。

        Args:
            output_dir: 分片输出目录。
            source: 当前数据源定义。
            shard_size: 单个分片最大记录数。
            start_shard: 起始分片编号。
        """

        self.output_dir = output_dir
        self.source = source
        self.shard_size = shard_size
        self.shard_index = start_shard
        self.records_in_shard = 0
        self.total_written = 0
        self._file: gzip.GzipFile | None = None
        self.created_files: list[str] = []

    def _open_next(self) -> None:
        """关闭当前文件并打开下一个分片文件。"""

        self.close()
        filename = f"{self.source.key}-{self.shard_index:05d}.jsonl.gz"
        self._file = gzip.open(
            self.output_dir / filename,
            "wt",
            encoding="utf-8",
        )
        self.created_files.append(filename)
        self.shard_index += 1
        self.records_in_shard = 0

    def write(self, record: dict[str, Any]) -> None:
        """写入一条记录，并在达到阈值时自动切换分片。

        Args:
            record: 已规范化的知识记录。
        """

        if self._file is None or self.records_in_shard >= self.shard_size:
            self._open_next()
        assert self._file is not None
        self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.records_in_shard += 1
        self.total_written += 1

    def close(self) -> None:
        """刷新并关闭当前 gzip 分片。"""

        if self._file is not None:
            self._file.close()
            self._file = None


def pull_source(
    source: DatasetSource,
    output_dir: Path,
    manifest: dict[str, Any],
    limit: int,
    shard_size: int,
    timeout: int,
    resume: bool,
) -> int:
    """拉取单个数据源并更新清单状态。

    Args:
        source: 数据源定义。
        output_dir: 输出目录。
        manifest: 全局下载清单。
        limit: 本次最多导出的记录数，0 表示不限。
        shard_size: 单个分片最大记录数。
        timeout: 网络连接超时秒数。
        resume: 是否跳过此前已经处理的远端行。

    Returns:
        本次成功写入的记录数。
    """

    previous = manifest["sources"].get(source.key, {}) if resume else {}
    start_offset = int(previous.get("next_source_index", 0))
    start_shard = int(previous.get("next_shard_index", 0))
    previous_files = list(previous.get("files", []))
    writer = ShardWriter(output_dir, source, shard_size, start_shard)
    iterator = (
        iter_remote_jsonl(source.direct_train_url, timeout, start_offset)
        if source.direct_train_url
        else iter_huggingface_dataset(source, start_offset)
    )
    last_source_index = start_offset - 1
    started_at = time.monotonic()

    try:
        for source_index, row in iterator:
            last_source_index = source_index
            normalized = normalize_row(row, source, source_index)
            if normalized is None:
                continue
            writer.write(normalized)
            if writer.total_written % 1_000 == 0:
                print(
                    f"[{source.key}] 已写入 {writer.total_written:,} 条",
                    file=sys.stderr,
                )
            if limit > 0 and writer.total_written >= limit:
                break
    finally:
        writer.close()

    state = {
        "dataset": asdict(source),
        "next_source_index": last_source_index + 1,  # 下一个要处理的行索引
        "next_shard_index": writer.shard_index,  # 下一个要处理的分片索引
        "written_this_run": writer.total_written,  # 本次写入的记录数
        "written_total": int(previous.get("written_total", 0)) + writer.total_written,
        "files": previous_files + writer.created_files,
        "elapsed_seconds": round(time.monotonic() - started_at, 3),
        "updated_at": utc_now(),
    }
    manifest["sources"][source.key] = state
    manifest["updated_at"] = utc_now()
    write_manifest(output_dir / "manifest.json", manifest)
    return writer.total_written


def main() -> int:
    """按参数顺序执行多个数据源的流式下载。

    Returns:
        全部数据源成功时返回 0，网络或数据错误时返回 1。
    """

    args = parse_args()
    if args.limit < 0 or args.shard_size <= 0:
        print("--limit 不能为负数，--shard-size 必须大于 0。", file=sys.stderr)
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "manifest.json"
    manifest = read_manifest(manifest_path) if args.resume else read_manifest(Path("-"))
    total = 0

    try:
        for source_key in args.sources:
            total += pull_source(
                source=SOURCES[source_key],
                output_dir=args.output_dir,
                manifest=manifest,
                limit=args.limit,
                shard_size=args.shard_size,
                timeout=args.timeout,
                resume=args.resume,
            )
    except (HTTPError, URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as error:
        print(f"拉取失败：{error}", file=sys.stderr)
        return 1

    print(f"拉取完成，本次共写入 {total:,} 条，清单：{manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
