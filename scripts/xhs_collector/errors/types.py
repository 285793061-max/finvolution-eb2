from __future__ import annotations

from typing import Optional


class CrawlError(Exception):
    """Base exception for crawl errors."""
    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.message = message
        self.retryable = retryable


class RetryableError(CrawlError):
    """Error that can be retried."""
    def __init__(self, message: str):
        super().__init__(message, retryable=True)


class FatalError(CrawlError):
    """Error that should not be retried."""
    def __init__(self, message: str):
        super().__init__(message, retryable=False)


class ChallengeError(CrawlError):
    """Challenge/detection error (e.g., Cloudflare)."""
    def __init__(self, message: str, challenge_type: Optional[str] = None):
        super().__init__(message, retryable=True)
        self.challenge_type = challenge_type


class ProxyError(RetryableError):
    """Proxy-related error."""
    pass


class TimeoutError(RetryableError):
    """Request timeout error."""
    pass


class BlockedError(FatalError):
    """Blocked by the target site."""
    pass