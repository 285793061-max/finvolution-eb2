from __future__ import annotations

from .types import (
    CrawlError,
    RetryableError,
    FatalError,
    ChallengeError,
    ProxyError,
    TimeoutError,
    BlockedError,
)
from .classifier import ErrorClassifier, FailureReason, map_to_failure_reason

__all__ = [
    "CrawlError",
    "RetryableError",
    "FatalError",
    "ChallengeError",
    "ProxyError",
    "TimeoutError",
    "BlockedError",
    "ErrorClassifier",
    "FailureReason",
    "map_to_failure_reason",
]