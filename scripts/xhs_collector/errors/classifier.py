from __future__ import annotations

from enum import Enum
from typing import Optional

from .types import CrawlError


class FailureReason(str, Enum):
    """Reason for a proxy or session failure."""
    CLOUDFLARE_CHALLENGE = "cloudflare_challenge"
    HTTP_ERROR = "http_error"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    PROXY_ERROR = "proxy_error"
    CHALLENGE_DETECTED = "challenge_detected"
    UNKNOWN = "unknown"


class ErrorClassifier:
    """Classifies errors into failure reasons."""

    TIMEOUT_LIKE_ERRORS = [
        "TimeoutError",
        "timeout",
        "timed out",
        "net::ERR_TIMED_OUT",
    ]

    PROXY_ERRORS = [
        "ERR_PROXY_CONNECTION_FAILED",
        "ERR_TUNNEL_CONNECTION_FAILED",
        "ERR_PROXY_AUTH_FAILED",
        "ERR_NEED_TO_RETRY",
        "ERR_SOCKS_CONNECTION_FAILED",
        "proxy",
    ]

    BLOCKED_ERRORS = [
        "403",
        "blocked",
        "access denied",
        "forbidden",
    ]

    CHALLENGE_ERRORS = [
        "cloudflare",
        "CF_",
        "challenge",
        "captcha",
        "turnstile",
    ]

    @classmethod
    def classify(cls, error: Exception) -> FailureReason:
        """Classify an error into a FailureReason."""
        msg = str(error).lower()

        if cls._contains_any(msg, cls.CHALLENGE_ERRORS):
            return FailureReason.CLOUDFLARE_CHALLENGE

        if cls._contains_any(msg, cls.BLOCKED_ERRORS):
            return FailureReason.BLOCKED

        if cls._contains_any(msg, cls.PROXY_ERRORS):
            return FailureReason.PROXY_ERROR

        if cls._is_timeout(error, msg):
            return FailureReason.TIMEOUT

        return FailureReason.HTTP_ERROR

    @classmethod
    def _contains_any(cls, text: str, patterns: list[str]) -> bool:
        """Check if text contains any of the patterns."""
        return any(p.lower() in text for p in patterns)

    @classmethod
    def _is_timeout(cls, error: Exception, msg: str) -> bool:
        """Check if error is a timeout error."""
        error_name = error.__class__.__name__
        if error_name in cls.TIMEOUT_LIKE_ERRORS:
            return True
        if cls._contains_any(msg, cls.TIMEOUT_LIKE_ERRORS):
            return True
        return False


def map_to_failure_reason(error: Exception) -> FailureReason:
    """Convenience function to classify an error."""
    return ErrorClassifier.classify(error)