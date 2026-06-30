from __future__ import annotations

import json
import fcntl
from pathlib import Path
from typing import Optional
from datetime import datetime


class ProgressTracker:
    """
    File-based progress tracker with atomic counter updates.
    Uses file locking for safe concurrent access.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.home() / ".xhs_collector" / "progress"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._progress_file = self.data_dir / "progress.json"
        self._lock_file = self.data_dir / "progress.lock"

    def _load(self) -> dict:
        """Load progress data from file."""
        if not self._progress_file.exists():
            return {
                "items_collected": 0,
                "pages_scraped": 0,
                "started_at": None,
                "last_updated_at": None,
            }
        try:
            with self._progress_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "items_collected": 0,
                "pages_scraped": 0,
                "started_at": None,
                "last_updated_at": None,
            }

    def _save(self, data: dict) -> None:
        """Save progress data to file atomically."""
        # Write to temp file first
        temp_path = self._progress_file.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            f.sync()

        # Atomic rename
        temp_path.rename(self._progress_file)

    def _lock(self) -> None:
        """Acquire file lock."""
        self._lock_file.touch()
        with open(self._lock_file, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)

    def _unlock(self) -> None:
        """Release file lock."""
        with open(self._lock_file, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def increment_items(self, count: int = 1) -> int:
        """Increment items collected counter. Returns new total."""
        self._lock()
        try:
            data = self._load()
            data["items_collected"] = data.get("items_collected", 0) + count
            data["last_updated_at"] = datetime.now().isoformat()
            self._save(data)
            return data["items_collected"]
        finally:
            self._unlock()

    def increment_pages(self, count: int = 1) -> int:
        """Increment pages scraped counter. Returns new total."""
        self._lock()
        try:
            data = self._load()
            data["pages_scraped"] = data.get("pages_scraped", 0) + count
            data["last_updated_at"] = datetime.now().isoformat()
            self._save(data)
            return data["pages_scraped"]
        finally:
            self._unlock()

    def start(self) -> None:
        """Mark crawl as started."""
        self._lock()
        try:
            data = self._load()
            if not data.get("started_at"):
                data["started_at"] = datetime.now().isoformat()
            data["last_updated_at"] = datetime.now().isoformat()
            self._save(data)
        finally:
            self._unlock()

    def reset(self) -> None:
        """Reset all progress."""
        self._lock()
        try:
            self._save({
                "items_collected": 0,
                "pages_scraped": 0,
                "started_at": datetime.now().isoformat(),
                "last_updated_at": datetime.now().isoformat(),
            })
        finally:
            self._unlock()

    def get_stats(self) -> dict:
        """Get current progress stats."""
        data = self._load()
        return {
            "items_collected": data.get("items_collected", 0),
            "pages_scraped": data.get("pages_scraped", 0),
            "started_at": data.get("started_at"),
            "last_updated_at": data.get("last_updated_at"),
        }