from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CrawlLimits:
    """Crawl limits configuration."""
    max_items: int = 50
    max_pages: int = 8
    max_retries: int = 3
    retry_delay_s: float = 2.0
    page_timeout_s: float = 30.0

    def is_item_limit_reached(self, current_count: int) -> bool:
        """Check if item limit is reached."""
        return current_count >= self.max_items

    def is_page_limit_reached(self, current_pages: int) -> bool:
        """Check if page limit is reached."""
        return current_pages >= self.max_pages

    def should_retry(self, retry_count: int) -> bool:
        """Check if should retry based on retry count."""
        return retry_count < self.max_retries