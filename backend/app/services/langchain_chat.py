"""统一 LangChain v1 模型入口，保留兼容服务参数与完整 JSON 校验。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langsmith import tracing_context
from openai import APIConnectionError, APIStatusError, APITimeoutError


LOGGER = logging.getLogger("uvicorn.error.medical_rag.langchain")


class ModelCallError(ValueError):
    """不包含提示词、报告正文或密钥的模型调用错误。"""

    def __init__(self, message: str, status_code: int = 502) -> None:
        """保存可展示错误及对应 HTTP 状态。

        Args:
            message: 安全错误说明。
            status_code: 业务接口返回状态。
        """
        super().__init__(message)
        self.status_code = status_code


def parse_complete_json(content: str) -> dict[str, Any]:
    """解析完整顶层 JSON，拒绝把截断 JSON 内的子对象冒充完整报告。

    Args:
        content: 模型输出文本，可附带说明文字或一个 JSON 代码块。

    Returns:
        完整顶层 JSON 对象。
    """
    normalized = content.strip().lstrip("\ufeff")
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", normalized, re.S | re.I)
    if fenced:
        normalized = fenced.group(1).strip()
    start = normalized.find("{")
    if start < 0:
        raise ModelCallError("模型没有返回 JSON 对象")
    try:
        value, end = json.JSONDecoder().raw_decode(normalized[start:])
    except json.JSONDecodeError as error:
        raise ModelCallError("模型 JSON 不完整或格式错误") from error
    if not isinstance(value, dict) or normalized[start + end:].lstrip().startswith(("{", ",", "]")):
        raise ModelCallError("模型没有返回唯一的顶层 JSON 对象")
    return value


def complete_json(
    *,
    base_url: str | None,
    api_key: str | None,
    model: str | None,
    system_prompt: str,
    user_content: str | list[dict[str, Any]],
    timeout: int,
    max_tokens: int,
    enable_thinking: bool | None,
    request_id: str,
    stage: str,
    structured_method: str = "prompt",
) -> dict[str, Any]:
    """通过提示词管道和 ChatOpenAI 调用文本或视觉模型并校验输出。

    Args:
        base_url: 服务根地址或历史完整 Chat Completions 地址。
        api_key: 仅在服务端使用的密钥。
        model: 模型名称。
        system_prompt: 指定职责与 JSON 格式的提示词。
        user_content: 用户文本或图片内容块。
        timeout: 单次网络请求超时秒数。
        max_tokens: 本次输出 Token 上限。
        enable_thinking: 服务商自定义思考开关。
        request_id: 本地请求标识。
        stage: 日志阶段名称。
        structured_method: prompt 兼容模式或 json_mode 服务端 JSON 模式。

    Returns:
        完整且可解析的 JSON 对象；失败时抛出安全错误，不输出半份报告。
    """
    if not all((base_url, api_key, model)):
        raise ModelCallError("LLM_BASE_URL、LLM_API_KEY 或 LLM_MODEL 未配置", 503)
    if structured_method not in {"prompt", "json_mode"}:
        raise ModelCallError("LLM_STRUCTURED_METHOD 必须为 prompt 或 json_mode", 503)
    url = (base_url or "").rstrip("/").removesuffix("/chat/completions")
    extra_body = {"enable_thinking": enable_thinking} if enable_thinking is not None else {}
    chat = init_chat_model(
        model=model,
        model_provider="openai",
        base_url=url,
        api_key=api_key,
        temperature=0,
        timeout=timeout,
        max_tokens=max_tokens,
        max_retries=0,
        use_responses_api=False,
        extra_body=extra_body,
    )
    prompt = ChatPromptTemplate.from_messages([MessagesPlaceholder("messages")])
    runner = (
        chat.with_structured_output(method="json_mode", include_raw=True)
        if structured_method == "json_mode"
        else chat
    )
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_content)]
    LOGGER.info("[LLM请求] request_id=%s stage=%s model=%s backend=langchain max_tokens=%s",
                request_id, stage, model, max_tokens)
    try:
        # 医疗正文和图片不因外部环境的 LangSmith 配置被自动上传。
        with tracing_context(enabled=False):
            output = (prompt | runner).invoke(
                {"messages": messages},
                config={"run_name": stage, "metadata": {"request_id": request_id}},
            )
        raw = output["raw"] if structured_method == "json_mode" else output
        finish = raw.response_metadata.get("finish_reason", "unknown")
        LOGGER.info("[LLM响应] request_id=%s stage=%s model=%s finish_reason=%s",
                    request_id, stage, model, finish)
        if finish in {"length", "max_tokens"}:
            raise ModelCallError("模型输出达到长度上限；请提高输出 Token 配置或缩短资料")
        if finish == "content_filter" or raw.additional_kwargs.get("refusal"):
            raise ModelCallError("模型拒绝处理本次内容")
        content = raw.content
        if isinstance(content, list):
            content = "".join(
                item if isinstance(item, str) else str(item.get("text", ""))
                for item in content if isinstance(item, (dict, str))
            )
        # 不采用可能自动补全截断 JSON 的宽松解析器。
        return parse_complete_json(content)
    except APITimeoutError as error:
        raise ModelCallError("模型请求超时", 504) from error
    except APIConnectionError as error:
        raise ModelCallError("模型网络连接失败", 504) from error
    except APIStatusError as error:
        raise ModelCallError(f"模型服务返回 HTTP {error.status_code}，请检查接口与模型权限") from error
    except ModelCallError:
        raise
    except Exception as error:
        # SDK/Pydantic 异常可能携带完整输入，不把原始异常文本写入日志。
        raise ModelCallError(f"LangChain 模型响应处理失败（{type(error).__name__}）") from error
