from __future__ import annotations

from typing import Optional

from .base import ChallengePlugin
from .detector import ChallengeDetector


class CloudflareChallengeHandler(ChallengePlugin):
    """Handler for Cloudflare challenges."""

    def __init__(self):
        self.detector = ChallengeDetector()
        self._cf_clearance: Optional[str] = None

    @property
    def name(self) -> str:
        return "cloudflare"

    def set_cf_clearance(self, token: str) -> None:
        """Set the cf_clearance token for injection."""
        self._cf_clearance = token

    def get_cf_clearance(self) -> Optional[str]:
        """Get the cached cf_clearance token."""
        return self._cf_clearance

    def on_pre_navigation(self, context: dict) -> None:
        """Inject cf_clearance cookie if available."""
        # This would be called before navigation to inject cookies
        pass

    def on_post_navigation(self, context: dict) -> None:
        """Check for Cloudflare challenge after navigation."""
        # This would detect challenges and potentially solve them
        pass

    def enrich_payload(self, context: dict, payload: dict) -> dict:
        """Enrich payload with challenge information."""
        page = context.get("page")
        if not page:
            return payload

        # Try to detect challenge from page
        try:
            if hasattr(page, "evaluate"):
                result = page.evaluate("""
                    () => {
                        return {
                            title: document.title || '',
                            bodyText: document.body?.innerText || '',
                            html: document.documentElement?.outerHTML || ''
                        };
                    }
                """)
                challenge_type = self.detector.detect(
                    result.get("title", ""),
                    result.get("bodyText", ""),
                    result.get("html", ""),
                )
                if challenge_type:
                    payload["challenge"] = {
                        "type": challenge_type,
                        "detected": True,
                        "provider": "cloudflare",
                    }
        except Exception:
            pass

        return payload