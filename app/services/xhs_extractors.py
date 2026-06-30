from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, List, Optional


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    text = text.strip()
    text = _WHITESPACE_RE.sub(" ", text)
    return text


def stable_id(text: str, prefix: str = "xhs") -> str:
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{h}"


def dedupe_texts(texts: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for t in texts:
        nt = normalize_text(t)
        if not nt:
            continue
        if nt in seen:
            continue
        seen.add(nt)
        out.append(nt)
    return out


@dataclass(frozen=True)
class ExtractedItem:
    id: str
    text: str
    source_type: str = "xiaohongshu"
    created_at: str | None = None
    meta: dict[str, Any] | None = None


def texts_to_items(
    texts: Iterable[str],
    *,
    keyword: str,
    source_type: str = "xiaohongshu",
    captured_at: datetime | None = None,
    meta: dict[str, Any] | None = None,
) -> list[ExtractedItem]:
    captured_at = captured_at or datetime.now(timezone.utc)
    base_meta = {"keyword": keyword, "captured_at": captured_at.isoformat()}
    if meta:
        base_meta.update(meta)

    items: list[ExtractedItem] = []
    for t in texts:
        nt = normalize_text(t)
        if not nt:
            continue
        items.append(
            ExtractedItem(
                id=stable_id(nt),
                text=nt,
                source_type=source_type,
                created_at=None,
                meta=base_meta,
            )
        )
    return items


def ocr_extract_lines(image: Any) -> list[str]:
    """
    OCR 抽取（EasyOCR）。

    - image: PIL.Image.Image 或 numpy array（EasyOCR 支持）。
    - 返回：识别到的“文本行”（未去重）。
    """
    try:
        import easyocr  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "未安装 OCR 依赖 easyocr。请先 pip install -r requirements.txt"
        ) from e

    # EasyOCR Reader 初始化较慢，尽量复用（模块级缓存）
    global _EASYOCR_READER  # noqa: PLW0603
    try:
        _EASYOCR_READER  # type: ignore[name-defined]
    except Exception:
        _EASYOCR_READER = easyocr.Reader(["ch_sim", "en"], gpu=False)  # type: ignore[name-defined]

    reader = _EASYOCR_READER  # type: ignore[name-defined]
    results = reader.readtext(image, detail=0, paragraph=False)
    return [str(x) for x in results if x]


def keyword_filter(texts: Iterable[str], keyword: str) -> list[str]:
    kw = keyword.strip().lower()
    if not kw:
        return [normalize_text(t) for t in texts if normalize_text(t)]
    out: list[str] = []
    for t in texts:
        nt = normalize_text(t)
        if not nt:
            continue
        if kw in nt.lower():
            out.append(nt)
    return out


def dom_extract_texts_from_html(html: str) -> list[str]:
    """
    DOM 抽取的兜底实现：从 HTML 中提取可见文本（非常粗糙，偏“应急”）。
    """
    # 尽量不引入 BeautifulSoup 之类的依赖，先做简单清洗
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    html = _WHITESPACE_RE.sub(" ", html).strip()
    # 过长文本切片，避免把整页导航文案塞进去
    if len(html) > 20000:
        html = html[:20000]
    # 简单按句子切分
    parts = re.split(r"[。！？\n]", html)
    return [p.strip() for p in parts if p.strip()]
