from __future__ import annotations

from pathlib import Path
from typing import Optional

from .store import JsonCacheStore


class CacheManager:
    """
    Cache manager for skipping known item IDs.
    File-based JSON storage with TTL support.
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        ttl_seconds: int = 3600,
    ):
        self.data_dir = data_dir or Path.home() / ".xhs_collector" / "cache"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self._item_cache = JsonCacheStore(self.data_dir / "items.json")
        self._id_cache = JsonCacheStore(self.data_dir / "ids.json")

    def is_item_cached(self, item_id: str) -> bool:
        """Check if an item ID is in the cache."""
        return self._id_cache.has(item_id)

    def add_item(self, item_id: str, item_data: dict) -> None:
        """Add an item to the cache."""
        self._item_cache.set(item_id, item_data, self.ttl_seconds)
        self._id_cache.set(item_id, True, self.ttl_seconds)

    def get_item(self, item_id: str) -> Optional[dict]:
        """Get cached item data."""
        return self._item_cache.get(item_id)

    def skip_item(self, item_id: str) -> bool:
        """Check if item should be skipped (already cached)."""
        if self.is_item_cached(item_id):
            return True
        return False

    def clear(self) -> None:
        """Clear all caches."""
        self._item_cache.clear()
        self._id_cache.clear()