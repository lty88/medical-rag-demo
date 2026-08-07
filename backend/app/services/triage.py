"""优先于检索和生成执行的急症危险信号规则。"""

from __future__ import annotations

from dataclasses import dataclass

from app.models import ConsultationRequest
from app.services.text import contains_any


@dataclass(frozen=True)
class RedFlagRule:
    """单条危险信号规则。"""

    key: str
    label: str
    any_terms: tuple[str, ...]
    supporting_terms: tuple[str, ...] = ()


RED_FLAG_RULES: tuple[RedFlagRule, ...] = (
    RedFlagRule(
        "breathing",
        "严重呼吸困难或发绀",
        ("喘不上气", "无法呼吸", "呼吸困难", "嘴唇发紫", "发绀", "说不出完整句子"),
        ("严重", "突然", "加重", "胸痛"),
    ),
    RedFlagRule(
        "cardiac",
        "可能的急性心血管危险信号",
        ("胸痛", "胸闷", "胸口压榨", "胸口撕裂"),
        ("大汗", "呼吸困难", "左臂", "下颌", "晕厥", "突然"),
    ),
    RedFlagRule(
        "stroke",
        "可能的卒中危险信号",
        ("口角歪", "一侧无力", "单侧无力", "说话含糊", "突然失语", "面歪"),
    ),
    RedFlagRule(
        "consciousness",
        "意识障碍、抽搐或昏厥",
        ("昏迷", "意识不清", "叫不醒", "持续抽搐", "反复抽搐", "晕厥"),
    ),
    RedFlagRule(
        "bleeding",
        "可能的大量出血",
        ("大量出血", "吐血", "咯血", "便血不止", "黑便伴头晕"),
    ),
    RedFlagRule(
        "allergy",
        "可能的严重过敏反应",
        ("喉咙肿", "舌头肿", "全身风团", "过敏性休克"),
        ("呼吸困难", "晕厥", "突然"),
    ),
    RedFlagRule(
        "self_harm",
        "自伤或自杀风险",
        ("想自杀", "不想活", "伤害自己", "自残计划", "服药自杀"),
    ),
)


def evaluate_red_flags(request: ConsultationRequest, text: str) -> list[str]:
    """根据症状、人群和体温识别需立即升级处理的危险信号。

    Args:
        request: 用户的人群与测量信息。
        text: 已脱敏的完整症状描述。

    Returns:
        命中的危险信号说明列表；空列表代表规则未命中。
    """

    hits: list[str] = []
    for rule in RED_FLAG_RULES:
        if not contains_any(text, rule.any_terms):
            continue
        if rule.supporting_terms and not contains_any(text, rule.supporting_terms):
            generic_terms = {"呼吸困难", "胸痛", "胸闷", "全身风团"}
            if rule.key in {"breathing", "cardiac", "allergy"} and contains_any(
                text, generic_terms
            ):
                continue
        hits.append(rule.label)

    if request.pregnant and contains_any(
        text, ("大量出血", "阴道出血", "剧烈腹痛", "胎动消失", "抽搐")
    ):
        hits.append("孕期出血、剧烈腹痛、抽搐或胎动异常")
    if request.age < 0.25 and request.temperature is not None and request.temperature >= 38:
        hits.append("3 月龄以下婴儿体温达到或超过 38℃")
    return list(dict.fromkeys(hits))
