from __future__ import annotations

from typing import Protocol, Optional
from dataclasses import dataclass


class PreNavigationHook(Protocol):
    """Protocol for pre-navigation hooks."""

    def before_navigation(self, context: dict) -> None:
        """Called before navigation occurs."""
        ...


class PostNavigationHook(Protocol):
    """Protocol for post-navigation hooks."""

    def after_navigation(self, context: dict) -> None:
        """Called after navigation occurs."""
        ...


@dataclass
class HookContext:
    """Context passed to hooks."""
    engine_name: str
    keyword: str
    page: Optional[object] = None
    session_id: Optional[str] = None
    proxy_url: Optional[str] = None
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class HookManager:
    """Manages pre and post navigation hooks."""

    def __init__(self):
        self._pre_hooks: list[PreNavigationHook] = []
        self._post_hooks: list[PostNavigationHook] = []

    def register_pre_hook(self, hook: PreNavigationHook) -> None:
        """Register a pre-navigation hook."""
        self._pre_hooks.append(hook)

    def register_post_hook(self, hook: PostNavigationHook) -> None:
        """Register a post-navigation hook."""
        self._post_hooks.append(hook)

    def run_pre_hooks(self, context: HookContext) -> None:
        """Run all pre-navigation hooks."""
        for hook in self._pre_hooks:
            try:
                hook.before_navigation(context.__dict__ if isinstance(context, HookContext) else {})
            except Exception as e:
                print(f"[HookManager] Pre-hook {hook.__class__.__name__} failed: {e}")

    def run_post_hooks(self, context: HookContext) -> None:
        """Run all post-navigation hooks."""
        for hook in self._post_hooks:
            try:
                hook.after_navigation(context.__dict__ if isinstance(context, HookContext) else {})
            except Exception as e:
                print(f"[HookManager] Post-hook {hook.__class__.__name__} failed: {e}")