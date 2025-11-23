"""
Robots.txt compliance checker for web scraping.

Checks and respects robots.txt directives to ensure ethical scraping.
"""

import urllib.robotparser
from urllib.parse import urlparse, urljoin
from typing import Optional, Dict
import time
import threading


class RobotsChecker:
    """
    Checks robots.txt compliance for URLs.

    Caches robots.txt parsers for efficiency and provides
    methods to check if URLs can be scraped.
    """

    def __init__(
        self,
        user_agent: str = "*",
        respect_robots_txt: bool = True,
        cache_timeout: int = 3600  # 1 hour
    ):
        """
        Initialize robots.txt checker.

        Args:
            user_agent: User-agent string for robots.txt checking
            respect_robots_txt: Whether to respect robots.txt
            cache_timeout: Cache timeout in seconds
        """
        self.user_agent = user_agent
        self.respect_robots_txt = respect_robots_txt
        self.cache_timeout = cache_timeout

        # Cache for robots.txt parsers
        self.parsers: Dict[str, Dict] = {}
        self.lock = threading.Lock()

        # Statistics
        self.stats = {
            "total_checks": 0,
            "allowed": 0,
            "disallowed": 0,
            "errors": 0
        }

    def _get_robots_url(self, url: str) -> str:
        """
        Get robots.txt URL for a given URL.

        Args:
            url: URL to get robots.txt for

        Returns:
            robots.txt URL
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def _get_parser(self, url: str) -> Optional[urllib.robotparser.RobotFileParser]:
        """
        Get or create robots.txt parser for a URL.

        Args:
            url: URL to get parser for

        Returns:
            RobotFileParser instance or None if failed
        """
        robots_url = self._get_robots_url(url)

        with self.lock:
            # Check cache
            if robots_url in self.parsers:
                cached = self.parsers[robots_url]
                # Check if cache is still valid
                if time.time() - cached["timestamp"] < self.cache_timeout:
                    return cached["parser"]

            # Create new parser
            try:
                parser = urllib.robotparser.RobotFileParser()
                parser.set_url(robots_url)
                parser.read()

                # Cache parser
                self.parsers[robots_url] = {
                    "parser": parser,
                    "timestamp": time.time()
                }

                return parser

            except Exception as e:
                # If robots.txt doesn't exist or can't be read, allow by default
                self.stats["errors"] += 1
                return None

    def can_fetch(self, url: str, user_agent: Optional[str] = None) -> bool:
        """
        Check if URL can be fetched according to robots.txt.

        Args:
            url: URL to check
            user_agent: User-agent to check for (optional)

        Returns:
            True if URL can be fetched, False otherwise
        """
        self.stats["total_checks"] += 1

        # If not respecting robots.txt, allow everything
        if not self.respect_robots_txt:
            self.stats["allowed"] += 1
            return True

        try:
            parser = self._get_parser(url)

            # If no parser (robots.txt doesn't exist or failed), allow by default
            if parser is None:
                self.stats["allowed"] += 1
                return True

            # Check if fetch is allowed
            ua = user_agent or self.user_agent
            allowed = parser.can_fetch(ua, url)

            if allowed:
                self.stats["allowed"] += 1
            else:
                self.stats["disallowed"] += 1

            return allowed

        except Exception:
            # On error, allow by default
            self.stats["errors"] += 1
            self.stats["allowed"] += 1
            return True

    def get_crawl_delay(self, url: str, user_agent: Optional[str] = None) -> Optional[float]:
        """
        Get crawl delay from robots.txt.

        Args:
            url: URL to get crawl delay for
            user_agent: User-agent to check for (optional)

        Returns:
            Crawl delay in seconds or None if not specified
        """
        if not self.respect_robots_txt:
            return None

        try:
            parser = self._get_parser(url)
            if parser is None:
                return None

            ua = user_agent or self.user_agent
            delay = parser.crawl_delay(ua)

            return float(delay) if delay else None

        except Exception:
            return None

    def get_request_rate(self, url: str, user_agent: Optional[str] = None) -> Optional[tuple]:
        """
        Get request rate from robots.txt.

        Args:
            url: URL to get request rate for
            user_agent: User-agent to check for (optional)

        Returns:
            Tuple of (requests, seconds) or None if not specified
        """
        if not self.respect_robots_txt:
            return None

        try:
            parser = self._get_parser(url)
            if parser is None:
                return None

            ua = user_agent or self.user_agent
            rate = parser.request_rate(ua)

            return rate

        except Exception:
            return None

    def is_sitemap_allowed(self, url: str) -> bool:
        """
        Check if sitemap is mentioned in robots.txt.

        Args:
            url: URL to check

        Returns:
            True if sitemap is mentioned
        """
        try:
            parser = self._get_parser(url)
            if parser is None:
                return False

            # Check if there are any sitemaps
            return len(parser.site_maps() or []) > 0

        except Exception:
            return False

    def get_sitemaps(self, url: str) -> list:
        """
        Get sitemap URLs from robots.txt.

        Args:
            url: URL to get sitemaps for

        Returns:
            List of sitemap URLs
        """
        try:
            parser = self._get_parser(url)
            if parser is None:
                return []

            sitemaps = parser.site_maps()
            return list(sitemaps) if sitemaps else []

        except Exception:
            return []

    def clear_cache(self) -> None:
        """Clear the robots.txt cache."""
        with self.lock:
            self.parsers.clear()

    def get_stats(self) -> dict:
        """
        Get checker statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            **self.stats,
            "cached_domains": len(self.parsers),
            "respect_robots_txt": self.respect_robots_txt
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = {
            "total_checks": 0,
            "allowed": 0,
            "disallowed": 0,
            "errors": 0
        }
