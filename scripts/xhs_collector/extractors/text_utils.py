from __future__ import annotations

# Re-export text utilities from the original xhs_extractors.py
# This ensures backward compatibility while allowing the collector module
# to use these functions directly

from app.services.xhs_extractors import (  # noqa: F401
    normalize_text,
    dedupe_texts,
    keyword_filter,
    ocr_extract_lines,
    texts_to_items,
    stable_id,
    ExtractedItem,
)

__all__ = [
    "normalize_text",
    "dedupe_texts",
    "keyword_filter",
    "ocr_extract_lines",
    "texts_to_items",
    "stable_id",
    "ExtractedItem",
]