"""中文检索所需的轻量文本处理。"""

from __future__ import annotations

import re


CJK_PATTERN = re.compile(r"[\u3400-\u9fff]+")
LATIN_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._+-]*")
STOPWORDS = {
    "什么",
    "怎么",
    "可以",
    "是否",
    "有些",
    "哪些",
    "一下",
    "感觉",
    "可能",
    "需要",
}


def tokenize(text: str) -> list[str]:
    """把中英文混合文本切为适合医疗关键词检索的词元。

    Args:
        text: 待处理文本。

    Returns:
        中文单字、双字片段和英文数字词元组成的列表。
    """

    normalized = text.lower().strip()
    tokens: list[str] = []
    for block in CJK_PATTERN.findall(normalized):
        tokens.extend(char for char in block if char.strip())
        tokens.extend(block[index : index + 2] for index in range(len(block) - 1))
    tokens.extend(match.group(0) for match in LATIN_PATTERN.finditer(normalized))
    return [token for token in tokens if token not in STOPWORDS]


def contains_any(text: str, terms: set[str] | list[str] | tuple[str, ...]) -> bool:
    """判断文本是否包含给定词组中的任意一个。

    Args:
        text: 要检查的文本。
        terms: 候选关键词集合。

    Returns:
        至少匹配一个关键词时返回真。
    """

    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def excerpt(text: str, limit: int = 140) -> str:
    """生成适合界面展示的单行证据摘要。

    Args:
        text: 原始证据文本。
        limit: 最大字符数。

    Returns:
        清理空白并按长度截断后的文本。
    """

    compact = re.sub(r"\s+", " ", text).strip()
    return compact if len(compact) <= limit else f"{compact[:limit]}…"
