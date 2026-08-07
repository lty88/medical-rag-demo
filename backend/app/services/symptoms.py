"""把自由文本转换成可展示、可检索的症状结构。"""

from __future__ import annotations

import re
from typing import Any

from app.models import ConsultationRequest


BODY_PARTS = (
    "头",
    "眼",
    "耳",
    "鼻",
    "咽",
    "胸",
    "腹",
    "腰",
    "背",
    "皮肤",
    "手",
    "腿",
    "关节",
)
SYMPTOM_TERMS = (
    "疼痛",
    "痛",
    "发热",
    "发烧",
    "咳嗽",
    "呕吐",
    "恶心",
    "腹泻",
    "头晕",
    "乏力",
    "皮疹",
    "瘙痒",
    "心悸",
    "胸闷",
    "呼吸困难",
    "失眠",
)


def structure_symptoms(request: ConsultationRequest, text: str) -> dict[str, Any]:
    """从自由描述中抽取症状词、部位、持续时间和人群条件。

    Args:
        request: 用户提交的结构化字段。
        text: 已脱敏的症状描述。

    Returns:
        供前端展示和后续检索使用的症状结构。
    """

    symptom_matches = [term for term in SYMPTOM_TERMS if term in text]
    body_matches = [term for term in BODY_PARTS if term in text]
    duration_match = re.search(r"\d+(?:\.\d+)?\s*(?:分钟|小时|天|周|个月|年)", text)
    return {
        "symptoms": list(dict.fromkeys(symptom_matches)),
        "body_parts": list(dict.fromkeys(body_matches)),
        "duration": request.duration or (duration_match.group(0) if duration_match else None),
        "temperature": request.temperature,
        "age": request.age,
        "sex": request.sex,
        "pregnant": request.pregnant,
        "region": request.region.upper(),
        "missing": build_follow_up_questions(request, text),
    }


def build_follow_up_questions(request: ConsultationRequest, text: str) -> list[str]:
    """根据缺失的关键病史生成有限的补充问题。

    Args:
        request: 用户提交的结构化字段。
        text: 已脱敏的症状描述。

    Returns:
        最多四个有助于分诊的追问。
    """

    questions: list[str] = []
    if not request.duration and not re.search(r"\d+\s*(?:分钟|小时|天|周|月|年)", text):
        questions.append("症状从什么时候开始，是持续存在还是间歇出现？")
    if not any(term in text for term in ("轻微", "中度", "严重", "剧烈", "评分")):
        questions.append("症状严重程度如何，是否影响说话、走路、进食或睡眠？")
    if not any(term in text for term in ("用药", "药物", "过敏", "慢性病", "基础病")):
        questions.append("是否有慢性病、药物过敏或正在使用的药物？")
    if request.temperature is None and any(term in text for term in ("发热", "发烧", "畏寒")):
        questions.append("请用可靠体温计测量并补充当前体温。")
    return questions[:4]
