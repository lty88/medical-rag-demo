"""用户输入中的常见隐私字段脱敏。"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PrivacyResult:
    """脱敏后的文本与命中类型。"""

    text: str
    redacted_types: tuple[str, ...]


PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("手机号", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "[手机号已脱敏]"),
    (
        "身份证号",
        re.compile(r"(?<![\dXx])\d{17}[\dXx](?![\dXx])"),
        "[身份证号已脱敏]",
    ),
    (
        "邮箱",
        re.compile(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}"),
        "[邮箱已脱敏]",
    ),
    (
        "详细地址",
        re.compile(r"(?:住址|地址)[:：]?[^，。；\n]{5,60}"),
        "地址：[详细地址已脱敏]",
    ),
)


def redact_privacy(text: str) -> PrivacyResult:
    """替换手机号、身份证、邮箱和显式地址等常见隐私信息。

    Args:
        text: 用户输入原文。

    Returns:
        脱敏后的文本及实际命中的隐私类型。
    """

    redacted = text
    matched: list[str] = []
    for name, pattern, replacement in PATTERNS:
        redacted, count = pattern.subn(replacement, redacted)
        if count:
            matched.append(name)
    return PrivacyResult(text=redacted, redacted_types=tuple(matched))
