from __future__ import annotations

from typing import Optional

from .base import ChallengePlugin


class ChallengeOrchestrator:
    """Orchestrates multiple challenge plugins."""

    def __init__(self, plugins: list[ChallengePlugin] | None = None):
        self.plugins: list[ChallengePlugin] = plugins or []

    def add_plugin(self, plugin: ChallengePlugin) -> None:
        """Add a challenge plugin."""
        self.plugins.append(plugin)

    def on_pre_navigation(self, context: dict) -> None:
        """Call pre-navigation hooks on all plugins."""
        for plugin in self.plugins:
            try:
                plugin.on_pre_navigation(context)
            except Exception as e:
                print(f"[ChallengeOrchestrator] pre hook failed for {plugin.name}: {e}")

    def on_post_navigation(self, context: dict) -> None:
        """Call post-navigation hooks on all plugins."""
        for plugin in self.plugins:
            try:
                plugin.on_post_navigation(context)
            except Exception as e:
                print(f"[ChallengeOrchestrator] post hook failed for {plugin.name}: {e}")

    def enrich_payload(self, context: dict, payload: dict) -> dict:
        """Enrich payload through all plugins."""
        result = payload
        for plugin in self.plugins:
            try:
                result = plugin.enrich_payload(context, result)
            except Exception as e:
                print(f"[ChallengeOrchestrator] enrich failed for {plugin.name}: {e}")
        return result