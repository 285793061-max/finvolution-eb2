from __future__ import annotations

import re
from typing import Optional


class ChallengeDetector:
    """Detects challenges using pattern matching."""

    # Cloudflare detection patterns
    CLOUDFLARE_TITLE_MARKERS = [
        "just a moment",
        "checking your browser",
        "performing security verification",
    ]

    CLOUDFLARE_BODY_MARKERS = [
        "enable javascript and cookies to continue",
        "security service to protect itself from online attacks",
        "attention required",
        "cloudflare",
        "ray id",
    ]

    CLOUDFLARE_HTML_MARKERS = [
        "challenge-platform",
        "challenge-running",
        "challenge-stage",
        "cf-chl-widget",
        "challenges.cloudflare.com",
        "/cdn-cgi/challenge-platform/",
        "cf-turnstile",
    ]

    def __init__(self):
        self._title_re = re.compile(
            "|".join(m.replace(" ", r"\s+") for m in self.CLOUDFLARE_TITLE_MARKERS),
            re.IGNORECASE,
        )
        self._body_markers_lower = [m.lower() for m in self.CLOUDFLARE_BODY_MARKERS]
        self._html_markers_lower = [m.lower() for m in self.CLOUDFLARE_HTML_MARKERS]

    def detect_cloudflare(self, title: str, body: str, html: str) -> bool:
        """Detect Cloudflare challenge page."""
        title_lower = title.lower()
        body_lower = body.lower()
        html_lower = html.lower()

        # Check title
        if self._title_re.search(title_lower):
            return True

        # Check body markers
        if any(m in body_lower for m in self._body_markers_lower):
            return True

        # Check HTML markers
        if any(m in html_lower for m in self._html_markers_lower):
            return True

        return False

    def detect(self, title: str, body: str, html: str) -> Optional[str]:
        """Detect any challenge type. Returns challenge type or None."""
        if self.detect_cloudflare(title, body, html):
            return "cloudflare"
        return None