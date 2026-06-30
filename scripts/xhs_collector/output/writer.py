from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import List

from app.services.xhs_extractors import ExtractedItem
from .legacy import write_latest as _write_latest_legacy


class OutputWriter:
    """
    Output writer with atomic writes.
    Wraps the legacy write_latest with atomic file operations.
    """

    def __init__(self, output_path: Path):
        self.output_path = output_path

    def write(self, items: List[ExtractedItem]) -> None:
        """Write items to output file atomically."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first, then atomic rename
        temp_fd, temp_path = tempfile.mkstemp(
            suffix=".tmp",
            prefix="xiaohongshu_",
            dir=self.output_path.parent,
        )

        try:
            import os
            from dataclasses import asdict

            payload = []
            for it in items:
                row = asdict(it)
                meta = row.pop("meta", None) or {}
                row.update(meta=meta)
                payload.append(row)

            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
                f.flush()
                f.sync()

            # Atomic rename
            Path(temp_path).rename(self.output_path)
        except Exception:
            # Clean up temp file on error
            try:
                Path(temp_path).unlink()
            except Exception:
                pass
            raise

    def write_legacy(self, items: List[ExtractedItem]) -> None:
        """Write using the legacy method (for backward compatibility)."""
        _write_latest_legacy(items, self.output_path)