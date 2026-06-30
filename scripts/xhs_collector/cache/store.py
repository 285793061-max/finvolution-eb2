from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Any
from datetime import datetime, timezone


class JsonCacheStore:
    """File-based JSON cache store with TTL support."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """Load cache from file."""
        if self.file_path.exists():
            try:
                with self.file_path.open("r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}

    def _save(self) -> None:
        """Save cache to file atomically."""
        temp_path = self.file_path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)
            f.flush()
            f.sync()
        temp_path.rename(self.file_path)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache, respecting TTL."""
        entry = self._cache.get(key)
        if not entry:
            return None

        # Check TTL if present
        if "expires_at" in entry:
            expires_at = entry["expires_at"]
            if expires_at and datetime.now(timezone.utc).timestamp() > expires_at:
                # Expired
                del self._cache[key]
                self._save()
                return None

        return entry.get("value")

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        entry: dict[str, Any] = {"value": value}

        if ttl_seconds is not None and ttl_seconds > 0:
            entry["expires_at"] = datetime.now(timezone.utc).timestamp() + ttl_seconds
        else:
            entry["expires_at"] = None

        entry["created_at"] = datetime.now(timezone.utc).isoformat()
        self._cache[key] = entry
        self._save()

    def delete(self, key: str) -> None:
        """Delete a key from cache."""
        if key in self._cache:
            del self._cache[key]
            self._save()

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._save()

    def has(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        return self.get(key) is not None