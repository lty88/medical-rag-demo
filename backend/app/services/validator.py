"""生成后执行引用、数字、诊断和治疗权限校验。"""

from __future__ import annotations

import re

from app.models import RankedDocument
from app.services.generator import GeneratedAnswer


CITATION_PATTERN = re.compile(r"\[(S\d+)\]")
NUMBER_PATTERN = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?(?:\s*(?:mg|g|ml|次|天|周|月|℃|%))?", re.I)
DIAGNOSIS_PATTERNS = ("你患有", "可以确诊", "诊断为", "确定是")
DOSAGE_PATTERN = re.compile(r"\d+(?:\.\d+)?\s*(?:mg|g|ml|片|粒|支).{0,12}(?:每日|每天|每次|口服)", re.I)


def validate_answer(
    answer: GeneratedAnswer,
    candidates: list[RankedDocument],
    treatment_intent: bool,
) -> list[str]:
    """阻止无出处陈述、未授权治疗和典型幻觉表达进入最终答案。

    Args:
        answer: 等待校验的生成结果。
        candidates: 实际提供给生成器的证据。
        treatment_intent: 用户是否请求治疗或剂量。

    Returns:
        校验问题列表；空列表表示通过。
    """

    issues: list[str] = []
    valid_markers = {citation.marker for citation in answer.citations}
    used_markers = set(CITATION_PATTERN.findall(answer.full_text))
    unknown_markers = used_markers - valid_markers
    if unknown_markers:
        issues.append(f"答案包含不存在的引用：{', '.join(sorted(unknown_markers))}")
    if answer.citations and not used_markers:
        issues.append("答案引用列表非空，但正文没有引用标记")
    if any(pattern in answer.full_text for pattern in DIAGNOSIS_PATTERNS):
        issues.append("答案包含未经允许的确定性诊断表达")

    authorized_treatment = any(
        candidate.document.allow_treatment_generation for candidate in candidates
    )
    if treatment_intent and not authorized_treatment:
        issues.append("当前证据均无治疗生成权限")
    if DOSAGE_PATTERN.search(answer.full_text) and not authorized_treatment:
        issues.append("答案包含未经高可信说明书支持的剂量表达")

    evidence_text = " ".join(candidate.document.content for candidate in candidates)
    generated_numbers = set(NUMBER_PATTERN.findall(answer.full_text))
    unsupported_numbers = {
        value for value in generated_numbers if value.strip() and value not in evidence_text
    }
    if unsupported_numbers:
        issues.append(f"答案包含证据中未出现的数字：{', '.join(sorted(unsupported_numbers))}")
    return issues
