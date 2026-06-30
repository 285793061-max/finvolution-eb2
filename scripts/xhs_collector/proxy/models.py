from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class FailureReason(str, Enum):
    """Reason for a proxy failure."""
    CLOUDFLARE_CHALLENGE = "cloudflare_challenge"
    HTTP_ERROR = "http_error"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    PROXY_ERROR = "proxy_error"
    UNKNOWN = "unknown"


@dataclass
class ProxyConfig:
    """Configuration for a proxy."""
    url: str
    enabled: bool = True
    last_failure_at: Optional[float] = None
    last_failure_reason: Optional[FailureReason] = None
    failure_count: int = 0
    last_success_at: Optional[float] = None

    @property
    def is_available(self) -> bool:
        """Check if proxy is available (not in failure cooldown)."""
        return self.enabled