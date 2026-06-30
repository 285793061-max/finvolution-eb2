from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime

from .models import ProxyConfig, FailureReason


class ProxyManager:
    """
    Proxy manager with file-based JSON storage and domain-level failure tracking.
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        failure_ttl_seconds: float = 7 * 24 * 60 * 60,  # 7 days
    ):
        self.data_dir = data_dir or Path.home() / ".xhs_collector" / "proxy"
        self.failure_ttl_seconds = failure_ttl_seconds
        self._cache: dict[str, dict] = {}
        self._load_cache()

    def _get_cache_path(self) -> Path:
        """Get path to the proxy cache file."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "proxy_cache.json"

    def _load_cache(self) -> None:
        """Load proxy cache from file."""
        cache_path = self._get_cache_path()
        if cache_path.exists():
            try:
                with cache_path.open("r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}

    def _save_cache(self) -> None:
        """Save proxy cache to file."""
        cache_path = self._get_cache_path()
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)

    def get_proxy_for_domain(self, domain: str) -> Optional[str]:
        """Get the working proxy URL for a domain from cache."""
        entry = self._cache.get(domain)
        if not entry:
            return None

        # Check if in failure cooldown
        last_failure = entry.get("last_failure_at")
        if last_failure:
            age_seconds = (datetime.now().timestamp() - last_failure)
            if age_seconds < self.failure_ttl_seconds:
                # Still in cooldown
                return None

        return entry.get("working_proxy_url")

    def record_domain_failure(
        self,
        domain: str,
        proxy_url: str,
        reason: FailureReason,
    ) -> None:
        """Record a failure for a domain/proxy combination."""
        now = datetime.now().timestamp()

        if domain not in self._cache:
            self._cache[domain] = {
                "working_proxy_url": None,
                "mode": "base",
                "total_failures": 0,
                "last_failure_at": None,
                "last_failure_reason": None,
            }

        self._cache[domain].update(
            last_failure_at=now,
            last_failure_reason=reason.value if isinstance(reason, FailureReason) else reason,
            total_failures=self._cache[domain].get("total_failures", 0) + 1,
        )
        self._save_cache()

    def record_domain_success(
        self,
        domain: str,
        proxy_url: str,
    ) -> None:
        """Record a success for a domain/proxy combination."""
        now = datetime.now().timestamp()

        if domain not in self._cache:
            self._cache[domain] = {
                "mode": "base",
                "total_failures": 0,
            }

        self._cache[domain].update(
            working_proxy_url=proxy_url,
            last_success_at=now,
            last_failure_at=None,
            last_failure_reason=None,
            total_failures=0,
        )
        self._save_cache()

    def clear_domain(self, domain: str) -> None:
        """Clear cache for a domain."""
        if domain in self._cache:
            del self._cache[domain]
            self._save_cache()

    @staticmethod
    def get_proxy_from_env() -> Optional[str]:
        """Get proxy URL from environment variable."""
        return os.environ.get("XHS_PROXY_URL")

    @staticmethod
    def get_proxy_from_config(config_path: Path) -> Optional[str]:
        """Get proxy URL from config file."""
        if not config_path.exists():
            return None
        try:
            with config_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("proxy_url")
        except Exception:
            return None