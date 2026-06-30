from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Session:
    """Represents a browser session with error scoring."""
    id: str
    error_score: int = 0
    max_error_score: int = 3
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    last_used_at: float = field(default_factory=lambda: datetime.now().timestamp())
    success_count: int = 0
    failure_count: int = 0

    @property
    def is_healthy(self) -> bool:
        """Check if session is still usable."""
        return self.error_score < self.max_error_score

    def record_success(self) -> None:
        """Record a successful request."""
        self.success_count += 1
        self.last_used_at = datetime.now().timestamp()
        # Decay error score on success
        self.error_score = max(0, self.error_score - 1)

    def record_failure(self, weight: int = 1) -> None:
        """Record a failed request."""
        self.failure_count += 1
        self.last_used_at = datetime.now().timestamp()
        self.error_score += weight


@dataclass
class SessionConfig:
    """Configuration for session management."""
    max_sessions: int = 5
    max_error_score: int = 3
    session_timeout_seconds: float = 3600
    error_score_increment: int = 1