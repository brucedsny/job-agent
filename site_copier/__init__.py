"""site_copier — copy an entire website for offline browsing.

A dependency-free (standard library only) website mirroring agent. It crawls a
site starting from a seed URL, downloads pages and their assets (CSS, JS,
images, fonts, ...) and rewrites the links so the copy can be browsed offline.
"""

from .crawler import SiteCopier, CrawlStats

__all__ = ["SiteCopier", "CrawlStats"]
__version__ = "0.1.0"
