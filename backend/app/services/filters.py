"""按年龄、孕期、地区和版本约束过滤候选证据。"""

from __future__ import annotations

from datetime import date

from app.models import ConsultationRequest, RankedDocument


def filter_candidates(
    request: ConsultationRequest, candidates: list[RankedDocument]
) -> tuple[list[RankedDocument], list[str]]:
    """剔除与用户人群或地区明确不兼容的文档。

    Args:
        request: 用户年龄、孕期和地区信息。
        candidates: 医疗精排后的候选证据。

    Returns:
        通过过滤的证据与汇总过滤原因。
    """

    accepted: list[RankedDocument] = []
    rejected_reasons: list[str] = []
    current_year = date.today().year

    for candidate in candidates:
        document = candidate.document
        reasons: list[str] = []
        if document.minimum_age is not None and request.age < document.minimum_age:
            reasons.append("低于文档适用年龄")
        if document.maximum_age is not None and request.age > document.maximum_age:
            reasons.append("高于文档适用年龄")
        if request.pregnant and document.pregnancy_allowed is False:
            reasons.append("文档明确不适用于孕期")
        region = request.region.upper()
        if document.regions and region not in document.regions and "GLOBAL" not in document.regions:
            reasons.append("地区不匹配")
        if document.guideline_version:
            try:
                version_year = int(document.guideline_version[:4])
                if current_year - version_year > 10:
                    candidate.filter_notes.append("指南版本超过十年，仅作历史参考")
            except ValueError:
                candidate.filter_notes.append("指南版本无法解析，需人工核对")

        if reasons:
            rejected_reasons.extend(f"{document.title}：{reason}" for reason in reasons)
            continue
        accepted.append(candidate)

    return accepted, rejected_reasons
