from __future__ import annotations

from typing import Callable, Optional
from .types import CrawlError, RetryableError, FatalError
from .classifier import FailureReason, ErrorClassifier


class ErrorHandler:
    """Registry for error handlers based on error type."""

    def __init__(self):
        self._handlers: dict[type, Callable[[Exception], Optional[str]]] = {}

    def register(self, error_type: type, handler: Callable[[Exception], Optional[str]]) -> None:
        """Register a handler for a specific error type."""
        self._handlers[error_type] = handler

    def handle(self, error: Exception) -> Optional[str]:
        """Handle an error and return a message if retryable."""
        for error_type, handler in self._handlers.items():
            if isinstance(error, error_type):
                return handler(error)
        return None

    def is_retryable(self, error: Exception) -> bool:
        """Check if an error is retryable."""
        if isinstance(error, RetryableError):
            return True
        if isinstance(error, FatalError):
            return False
        if isinstance(error, CrawlError):
            return error.retryable
        return True  # Default to retryable


# Global error handler registry
_handler_registry: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler registry."""
    global _handler_registry
    if _handler_registry is None:
        _handler_registry = ErrorHandler()
    return _handler_registry


def register_error_handler(error_type: type, handler: Callable[[Exception], Optional[str]]) -> None:
    """Register an error handler globally."""
    get_error_handler().register(error_type, handler)