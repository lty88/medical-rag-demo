"""受检索证据约束的结构化答案生成器。"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.models import AnswerSection, Citation, RankedDocument
from app.services.text import excerpt


LOGGER = logging.getLogger("uvicorn.error.medical_rag.llm")


@dataclass(frozen=True)
class GeneratedAnswer:
    """等待安全校验的生成结果。"""

    title: str
    summary: str
    sections: list[AnswerSection]
    citations: list[Citation]
    mode: str
    detail: str

    @property
    def full_text(self) -> str:
        """合并所有生成字段以供校验器扫描。

        Returns:
            标题、摘要和区块正文组成的文本。
        """

        return "\n".join(
            [self.title, self.summary, *(section.content for section in self.sections)]
        )


class EvidenceBoundGenerator:
    """支持 OpenAI 兼容接口、默认使用证据模板的生成器。"""

    def __init__(
        self,
        base_url: str | None,
        api_key: str | None,
        model: str | None,
        timeout_seconds: int = 180,
        evidence_max_characters: int = 2_500,
        max_output_tokens: int = 1_200,
        enable_thinking: bool | None = None,
    ) -> None:
        """保存显式提供的大模型配置。

        Args:
            base_url: OpenAI 兼容服务根地址。
            api_key: 服务访问密钥。
            model: 服务端模型名称。
            timeout_seconds: 单次大模型请求超时秒数。
            evidence_max_characters: 每条候选允许发送给大模型的最大字符数。
            max_output_tokens: 单次回答允许生成的最大 Token 数。
            enable_thinking: 是否启用服务商支持的思考模式；空值表示不发送该参数。
        """

        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.evidence_max_characters = evidence_max_characters
        self.max_output_tokens = max_output_tokens
        self.enable_thinking = enable_thinking

    def generate(
        self,
        query: str,
        candidates: list[RankedDocument],
        follow_up_questions: list[str],
        treatment_intent: bool,
        request_id: str = "unknown",
    ) -> GeneratedAnswer:
        """根据经过人群过滤的证据生成结构化回答。

        Args:
            query: 已脱敏的用户文本。
            candidates: 最终允许参与回答的候选证据。
            follow_up_questions: 症状结构化阶段产生的追问。
            treatment_intent: 用户是否请求治疗或剂量建议。
            request_id: 用于串联用户输入、检索和 LLM 日志的请求标识。

        Returns:
            带引用标记、等待校验的结构化答案。
        """

        citations = self._build_citations(candidates)
        missing = self._missing_configuration()
        if not missing and citations:
            try:
                return self._call_llm(
                    query,
                    candidates,
                    citations,
                    follow_up_questions,
                    request_id,
                )
            except (HTTPError, URLError, OSError, TimeoutError, ValueError, KeyError) as error:
                safe_detail = self._safe_error_detail(error)
                LOGGER.warning(
                    "[LLM失败] request_id=%s model=%s error=%s",
                    request_id,
                    self.model,
                    safe_detail,
                )
                return self._build_fallback(
                    candidates,
                    citations,
                    follow_up_questions,
                    treatment_intent,
                    detail=f"LLM 调用失败，已安全回退：{safe_detail}",
                )
        if missing:
            LOGGER.warning(
                "[LLM跳过] request_id=%s 缺少配置=%s",
                request_id,
                ",".join(missing),
            )
            return self._build_fallback(
                candidates,
                citations,
                follow_up_questions,
                treatment_intent,
                detail=f"LLM 配置不完整：缺少 {', '.join(missing)}",
            )
        LOGGER.warning(
            "[LLM跳过] request_id=%s 原因=没有通过人群过滤的检索证据",
            request_id,
        )
        return self._build_fallback(
            candidates,
            citations,
            follow_up_questions,
            treatment_intent,
            detail="没有通过人群过滤的检索证据，未调用 LLM",
        )

    def _missing_configuration(self) -> list[str]:
        """返回调用 OpenAI 兼容接口仍缺少的配置名称。

        Returns:
            缺失的 Base URL、API Key 或模型名称；配置完整时返回空列表。
        """

        values = {
            "LLM_BASE_URL": self.base_url,
            "LLM_API_KEY": self.api_key,
            "LLM_MODEL": self.model,
        }
        return [name for name, value in values.items() if not value]

    def _chat_completions_url(self) -> str:
        """兼容服务根地址和完整 Chat Completions 地址两种配置。

        Returns:
            可直接发送 POST 请求的 Chat Completions 地址。

        Raises:
            ValueError: Base URL 未配置时抛出。
        """

        if not self.base_url:
            raise ValueError("LLM_BASE_URL 未配置")
        normalized = self.base_url.rstrip("/")
        return (
            normalized
            if normalized.endswith("/chat/completions")
            else f"{normalized}/chat/completions"
        )

    def _safe_error_detail(self, error: Exception) -> str:
        """把接口异常转换为不包含密钥和响应正文的安全说明。

        Args:
            error: HTTP、网络、超时或响应解析异常。

        Returns:
            可展示在流水线轨迹中的简短失败原因。
        """

        if isinstance(error, HTTPError):
            return self._safe_http_error_detail(error)
        if isinstance(error, URLError):
            return f"网络连接失败：{error.reason}"
        if isinstance(error, TimeoutError):
            return "请求超时"
        return f"{type(error).__name__}: {str(error)[:180]}"

    def _safe_http_error_detail(self, error: HTTPError) -> str:
        """提取兼容接口 HTTP 错误中的公开诊断字段。

        Args:
            error: urllib 返回的 HTTP 状态异常。

        Returns:
            只包含状态、错误码、说明和请求标识的安全错误文本。
        """

        base_detail = f"HTTP {error.code} {error.reason}"
        try:
            raw_body = error.read(8_192).decode("utf-8", errors="replace")
            body = json.loads(raw_body)
        except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
            return base_detail
        if not isinstance(body, dict):
            return base_detail
        safe_fields: list[str] = []
        for key in ("code", "message", "request_id", "requestId"):
            value = body.get(key)
            if isinstance(value, (str, int, float)) and str(value).strip():
                safe_fields.append(f"{key}={str(value).strip()[:500]}")
        return f"{base_detail}；{'；'.join(safe_fields)}" if safe_fields else base_detail

    def _parse_json_content(self, content: str) -> dict[str, Any]:
        """解析大模型返回的纯 JSON 或 Markdown JSON 代码块。

        Args:
            content: Chat Completions 返回的消息正文。

        Returns:
            包含标题、摘要和章节的 JSON 对象。

        Raises:
            ValueError: 正文为空、不是 JSON 对象或缺少必要字段时抛出。
        """

        normalized = content.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", normalized, re.S | re.I)
        if fenced:
            normalized = fenced.group(1).strip()
        try:
            result = json.loads(normalized)
        except json.JSONDecodeError as error:
            raise ValueError("LLM 未返回有效 JSON") from error
        if not isinstance(result, dict):
            raise ValueError("LLM 返回结果不是 JSON 对象")
        if not result.get("title") or not result.get("summary"):
            raise ValueError("LLM 返回结果缺少 title 或 summary")
        if not isinstance(result.get("sections"), list) or not result["sections"]:
            raise ValueError("LLM 返回结果缺少有效 sections")
        return result

    def _build_citations(self, candidates: list[RankedDocument]) -> list[Citation]:
        """把候选文档转换为固定编号的引用对象。

        Args:
            candidates: 经过全部过滤的候选证据。

        Returns:
            顺序稳定的引用列表。
        """

        return [
            Citation(
                marker=f"S{index}",
                title=candidate.document.title,
                source=candidate.document.source,
                source_url=candidate.document.source_url,
                trust_level=candidate.document.trust_level,
                excerpt=excerpt(candidate.document.content),
                allow_treatment_generation=candidate.document.allow_treatment_generation,
            )
            for index, candidate in enumerate(candidates, start=1)
        ]

    def _call_llm(
        self,
        query: str,
        candidates: list[RankedDocument],
        citations: list[Citation],
        follow_up_questions: list[str],
        request_id: str,
    ) -> GeneratedAnswer:
        """调用显式配置的 OpenAI 兼容接口并解析限定 JSON。

        Args:
            query: 已脱敏的用户文本。
            candidates: 允许用于回答的候选证据。
            citations: 与候选证据对应的固定引用。
            follow_up_questions: 仍需用户补充的问题。
            request_id: 用于串联整条咨询链路的请求标识。

        Returns:
            从模型 JSON 响应构建的答案。
        """

        evidence = "\n\n".join(
            (
                f"[{citation.marker}]\n"
                f"标题：{candidate.document.title}\n"
                f"问题：{candidate.document.question or candidate.document.title}\n"
                f"来源：{candidate.document.source}\n"
                f"可信等级：{candidate.document.trust_level}\n"
                f"治疗生成权限："
                f"{'允许' if candidate.document.allow_treatment_generation else '不允许'}\n"
                f"证据正文：{candidate.document.content[:self.evidence_max_characters]}"
            )
            for citation, candidate in zip(citations, candidates, strict=False)
        )
        system_prompt = (
            "你是医疗 RAG 系统的证据摘要器，不做确诊，不替代医生。"
            "只能根据用户描述和检索证据作答，不得使用模型记忆补充证据外医学事实。"
            "每一项医学事实都必须在句末标注一个或多个证据编号，例如[S1]或[S1][S2]。"
            "证据标记为治疗生成权限不允许时，不得给出药名、剂量、处方、停药或治疗方案。"
            "如果证据互相冲突、与问题不匹配或不足，应明确说明证据不足。"
            "输出必须是JSON对象，且只能包含title、summary、sections三个字段；"
            "sections是由title和content组成的数组。"
        )
        user_prompt = (
            f"用户描述：\n{query}\n\n"
            f"系统建议追问：\n{'；'.join(follow_up_questions) or '无'}\n\n"
            f"最终检索证据：\n{evidence}"
        )
        payload_data: dict[str, Any] = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": self.max_output_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self.enable_thinking is not None:
            payload_data["enable_thinking"] = self.enable_thinking
        payload = json.dumps(
            payload_data,
            ensure_ascii=False,
        ).encode("utf-8")
        LOGGER.info(
            "[LLM请求] %s",
            json.dumps(
                {
                    "request_id": request_id,
                    "url": self._chat_completions_url(),
                    "prompt_characters": len(system_prompt) + len(user_prompt),
                    "timeout_seconds": self.timeout_seconds,
                    "payload": payload_data,
                },
                ensure_ascii=False,
            ),
        )
        request = Request(
            self._chat_completions_url(),
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started_at = time.perf_counter()
        with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
            response_data = json.loads(response.read().decode("utf-8"))
        duration_ms = round((time.perf_counter() - started_at) * 1000)
        content = str(response_data["choices"][0]["message"]["content"])
        LOGGER.info(
            "[LLM响应] %s",
            json.dumps(
                {
                    "request_id": request_id,
                    "model": self.model,
                    "duration_ms": duration_ms,
                    "content": content,
                    "usage": response_data.get("usage"),
                },
                ensure_ascii=False,
            ),
        )
        result = self._parse_json_content(content)
        sections = [AnswerSection.model_validate(item) for item in result["sections"]]
        return GeneratedAnswer(
            title=str(result["title"]),
            summary=str(result["summary"]),
            sections=sections,
            citations=citations,
            mode="configured-llm",
            detail=(
                f"已将 {len(candidates)} 条最终检索证据发送给模型 {self.model}，"
                "并收到结构化回答"
            ),
        )

    def _build_fallback(
        self,
        candidates: list[RankedDocument],
        citations: list[Citation],
        follow_up_questions: list[str],
        treatment_intent: bool,
        detail: str,
    ) -> GeneratedAnswer:
        """在未配置模型时生成完全可追溯的证据模板回答。

        Args:
            candidates: 最终候选证据。
            citations: 固定编号的引用对象。
            follow_up_questions: 尚需补充的问题。
            treatment_intent: 用户是否请求治疗或剂量建议。
            detail: 未调用或调用失败后回退的可观察原因。

        Returns:
            不引入证据外医学事实的模板答案。
        """

        if not candidates:
            return GeneratedAnswer(
                title="当前证据不足",
                summary="知识库没有找到与人群条件匹配的可用资料，系统不会继续推断。",
                sections=[
                    AnswerSection(
                        title="建议",
                        content="请补充症状细节，或携带完整病史向合格医疗专业人员咨询。",
                    )
                ],
                citations=[],
                mode="evidence-template",
                detail=detail,
            )

        evidence_lines = [
            f"{citation.excerpt} [{citation.marker}]" for citation in citations
        ]
        question_text = (
            "；".join(follow_up_questions)
            if follow_up_questions
            else "当前基础信息较完整；如症状变化，请及时补充。"
        )
        summary = (
            "检索到了相关资料，但这些证据没有治疗生成权限，不能据此给出具体治疗或剂量。"
            if treatment_intent
            else "以下内容是对检索证据的整理，不是诊断或个体化治疗方案。"
        )
        return GeneratedAnswer(
            title="基于当前资料的辅助信息",
            summary=summary,
            sections=[
                AnswerSection(title="检索到的相关信息", content="\n".join(evidence_lines)),
                AnswerSection(title="建议补充", content=question_text),
                AnswerSection(
                    title="安全边界",
                    content="如症状明显加重、出现新的危险信号或你感到情况紧急，请停止在线咨询并寻求线下医疗帮助。",
                ),
            ],
            citations=citations,
            mode="evidence-template",
            detail=detail,
        )
