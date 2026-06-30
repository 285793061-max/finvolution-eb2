from __future__ import annotations

import json
from pathlib import Path
from dataclasses import asdict
from typing import List

from app.services.xhs_extractors import ExtractedItem


def write_latest(items: List[ExtractedItem], out_path: Path) -> None:
    """
    Write items to xiaohongshu_latest.json.
    Identical to the original implementation in xhs_human_collect.py.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for it in items:
        row = asdict(it)
        meta = row.pop("meta", None) or {}
        row.update(meta=meta)
        payload.append(row)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)