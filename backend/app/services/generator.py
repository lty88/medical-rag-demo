"""受检索证据约束的结构化答案生成器。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen

from app.models import AnswerSection, Citation, RankedDocument
from app.services.text import excerpt


@dataclass(frozen=True)
class GeneratedAnswer:
    """等待安全校验的生成结果。"""

    title: str
    summary: str
    sections: list[AnswerSection]
    citations: list[Citation]
    mode: str

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
    ) -> None:
        """保存显式提供的大模型配置。

        Args:
            base_url: OpenAI 兼容服务根地址。
            api_key: 服务访问密钥。
            model: 服务端模型名称。
        """

        self.base_url = base_url
        self.api_key = api_key
        self.model = model

    def generate(
        self,
        query: str,
        candidates: list[RankedDocument],
        follow_up_questions: list[str],
        treatment_intent: bool,
    ) -> GeneratedAnswer:
        """根据经过人群过滤的证据生成结构化回答。

        Args:
            query: 已脱敏的用户文本。
            candidates: 最终允许参与回答的候选证据。
            follow_up_questions: 症状结构化阶段产生的追问。
            treatment_intent: 用户是否请求治疗或剂量建议。

        Returns:
            带引用标记、等待校验的结构化答案。
        """

        citations = self._build_citations(candidates)
        if self.base_url and self.api_key and self.model and citations:
            try:
                return self._call_llm(query, candidates, citations, follow_up_questions)
            except (OSError, TimeoutError, ValueError, KeyError, json.JSONDecodeError):
                pass
        return self._build_fallback(
            candidates, citations, follow_up_questions, treatment_intent
        )

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
    ) -> GeneratedAnswer:
        """调用显式配置的 OpenAI 兼容接口并解析限定 JSON。

        Args:
            query: 已脱敏的用户文本。
            candidates: 允许用于回答的候选证据。
            citations: 与候选证据对应的固定引用。
            follow_up_questions: 仍需用户补充的问题。

        Returns:
            从模型 JSON 响应构建的答案。
        """

        evidence = "\n".join(
            f"[{citation.marker}] {candidate.document.content}"
            for citation, candidate in zip(citations, candidates, strict=False)
        )
        prompt = (
            "你是医疗信息检索系统中的证据摘要器，不做诊断。"
            "只能使用给定证据，每项医学陈述结尾必须带[S数字]。"
            "不得补充药名、剂量或诊断。输出JSON，字段为title、summary、sections，"
            "sections是包含title和content的数组。\n"
            f"用户描述：{query}\n可用证据：\n{evidence}\n"
            f"仍需追问：{'；'.join(follow_up_questions) or '无'}"
        )
        payload = json.dumps(
            {
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode("utf-8")
        request = Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=45) as response:  # noqa: S310
            response_data = json.loads(response.read().decode("utf-8"))
        content = response_data["choices"][0]["message"]["content"]
        result: dict[str, Any] = json.loads(content)
        sections = [AnswerSection.model_validate(item) for item in result["sections"]]
        return GeneratedAnswer(
            title=str(result["title"]),
            summary=str(result["summary"]),
            sections=sections,
            citations=citations,
            mode="configured-llm",
        )

    def _build_fallback(
        self,
        candidates: list[RankedDocument],
        citations: list[Citation],
        follow_up_questions: list[str],
        treatment_intent: bool,
    ) -> GeneratedAnswer:
        """在未配置模型时生成完全可追溯的证据模板回答。

        Args:
            candidates: 最终候选证据。
            citations: 固定编号的引用对象。
            follow_up_questions: 尚需补充的问题。
            treatment_intent: 用户是否请求治疗或剂量建议。

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
        )
