from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import HookContext

from .manager import PostNavigationHook


class ChallengeSolvingHook(PostNavigationHook):
    """Post-navigation hook to solve challenges."""

    def __init__(self, challenge_orchestrator):
        self.challenge_orchestrator = challenge_orchestrator

    def after_navigation(self, context: dict) -> None:
        """Run post-navigation challenge solving."""
        self.challenge_orchestrator.on_post_navigation(context)


class ProgressUpdateHook(PostNavigationHook):
    """Post-navigation hook to update progress."""

    def __init__(self, progress_tracker):
        self.progress_tracker = progress_tracker

    def after_navigation(self, context: dict) -> None:
        """Update progress after navigation."""
        self.progress_tracker.increment_pages()


class CacheSaveHook(PostNavigationHook):
    """Post-navigation hook to save items to cache."""

    def __init__(self, cache_manager):
        self.cache_manager = cache_manager

    def after_navigation(self, context: dict) -> None:
        """Save collected items to cache."""
        pass