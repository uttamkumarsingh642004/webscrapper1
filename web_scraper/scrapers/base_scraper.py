"""
Base scraper abstract class.

Defines the interface and common functionality for all scrapers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import time
from urllib.parse import urljoin, urlparse
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from web_scraper.utils.logger import get_logger
from web_scraper.utils.rate_limiter import RateLimiter, AdaptiveRateLimiter
from web_scraper.utils.proxy_manager import ProxyManager
from web_scraper.utils.user_agent_rotator import UserAgentRotator
from web_scraper.utils.robots_checker import RobotsChecker


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.

    Provides common functionality including rate limiting,
    proxy support, user-agent rotation, and error handling.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the base scraper.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Initialize logger
        log_config = self.config.get("error_handling", {})
        self.logger = get_logger(
            name=self.__class__.__name__,
            log_level=log_config.get("log_level", "INFO"),
            log_file=log_config.get("log_file"),
            log_to_console=log_config.get("log_to_console", True)
        )

        # Initialize rate limiter
        scraping_config = self.config.get("scraping", {})
        rate_limit = scraping_config.get("rate_limit", 1.0)
        delay = scraping_config.get("delay_between_requests", 0)

        if scraping_config.get("adaptive_rate_limiting", False):
            self.rate_limiter = AdaptiveRateLimiter(
                initial_rate=rate_limit,
                delay_between_requests=delay
            )
        else:
            self.rate_limiter = RateLimiter(
                requests_per_second=rate_limit,
                delay_between_requests=delay
            )

        # Initialize proxy manager
        request_config = self.config.get("request", {})
        self.proxy_manager: Optional[ProxyManager] = None
        if request_config.get("use_proxy", False):
            proxy_file = request_config.get("proxy_file")
            if proxy_file:
                try:
                    self.proxy_manager = ProxyManager(
                        proxy_file=proxy_file,
                        rotation_strategy=request_config.get("proxy_rotation_strategy", "round_robin")
                    )
                    self.logger.info(f"Loaded proxies from {proxy_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to load proxies: {e}")

        # Initialize user-agent rotator
        self.ua_rotator = UserAgentRotator(
            custom_user_agents=request_config.get("custom_user_agents", []),
            use_fake_ua=request_config.get("rotate_user_agent", True)
        )

        # Initialize robots.txt checker
        advanced_config = self.config.get("advanced", {})
        self.robots_checker = RobotsChecker(
            respect_robots_txt=advanced_config.get("respect_robots_txt", True)
        )

        # Retry configuration
        self.max_retries = scraping_config.get("max_retries", 3)
        self.retry_delay = scraping_config.get("retry_delay", 1)
        self.backoff_factor = scraping_config.get("backoff_factor", 2)

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_items_scraped": 0,
            "start_time": None,
            "end_time": None
        }

        # Failed URLs tracking
        self.failed_urls: List[Dict[str, Any]] = []
        self.save_failed_urls = log_config.get("save_failed_urls", True)
        self.failed_urls_file = log_config.get("failed_urls_file", "failed_urls.txt")

    @abstractmethod
    def scrape(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Scrape data from a URL.

        Args:
            url: URL to scrape
            **kwargs: Additional scraper-specific arguments

        Returns:
            Dictionary containing scraped data
        """
        pass

    @abstractmethod
    def scrape_multiple(self, urls: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape data from multiple URLs.

        Args:
            urls: List of URLs to scrape
            **kwargs: Additional scraper-specific arguments

        Returns:
            List of dictionaries containing scraped data
        """
        pass

    def _check_robots_txt(self, url: str) -> bool:
        """
        Check if URL can be scraped according to robots.txt.

        Args:
            url: URL to check

        Returns:
            True if allowed, False otherwise
        """
        try:
            allowed = self.robots_checker.can_fetch(url)
            if not allowed:
                self.logger.warning(f"Robots.txt disallows scraping: {url}")
            return allowed
        except Exception as e:
            self.logger.error(f"Error checking robots.txt: {e}")
            return True  # Allow by default on error

    def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers with rotated user-agent.

        Returns:
            Dictionary of headers
        """
        headers = self.config.get("request", {}).get("headers", {}).copy()
        headers["User-Agent"] = self.ua_rotator.get_random_user_agent()
        return headers

    def _get_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get proxy configuration.

        Returns:
            Proxy dictionary or None
        """
        if self.proxy_manager:
            return self.proxy_manager.get_proxy()
        return None

    def _handle_request_success(self, url: str, proxy_url: Optional[str] = None) -> None:
        """
        Handle successful request.

        Args:
            url: URL that was successfully scraped
            proxy_url: Proxy URL that was used (optional)
        """
        self.stats["successful_requests"] += 1

        # Report to rate limiter if adaptive
        if isinstance(self.rate_limiter, AdaptiveRateLimiter):
            self.rate_limiter.report_success()

        # Report to proxy manager
        if proxy_url and self.proxy_manager:
            self.proxy_manager.report_success(proxy_url)

    def _handle_request_failure(
        self,
        url: str,
        error: Exception,
        proxy_url: Optional[str] = None
    ) -> None:
        """
        Handle failed request.

        Args:
            url: URL that failed
            error: Exception that occurred
            proxy_url: Proxy URL that was used (optional)
        """
        self.stats["failed_requests"] += 1

        # Log failure
        self.logger.error(f"Failed to scrape {url}: {str(error)}")

        # Track failed URL
        self.failed_urls.append({
            "url": url,
            "error": str(error),
            "timestamp": time.time()
        })

        # Report to rate limiter if adaptive
        if isinstance(self.rate_limiter, AdaptiveRateLimiter):
            self.rate_limiter.report_failure()

        # Report to proxy manager
        if proxy_url and self.proxy_manager:
            self.proxy_manager.report_failure(proxy_url)

    def _save_failed_urls(self) -> None:
        """Save failed URLs to file."""
        if not self.save_failed_urls or not self.failed_urls:
            return

        try:
            with open(self.failed_urls_file, 'w') as f:
                for failed in self.failed_urls:
                    f.write(f"{failed['url']}\t{failed['error']}\n")
            self.logger.info(f"Saved {len(self.failed_urls)} failed URLs to {self.failed_urls_file}")
        except Exception as e:
            self.logger.error(f"Failed to save failed URLs: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get scraper statistics.

        Returns:
            Dictionary with statistics
        """
        stats = self.stats.copy()

        # Calculate duration
        if stats["start_time"] and stats["end_time"]:
            stats["duration"] = stats["end_time"] - stats["start_time"]
            if stats["duration"] > 0:
                stats["requests_per_second"] = stats["total_requests"] / stats["duration"]

        # Add sub-component stats
        stats["rate_limiter"] = self.rate_limiter.get_stats()
        if self.proxy_manager:
            stats["proxy_manager"] = self.proxy_manager.get_stats()
        stats["user_agent_rotator"] = self.ua_rotator.get_stats()
        stats["robots_checker"] = self.robots_checker.get_stats()

        return stats

    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_items_scraped": 0,
            "start_time": None,
            "end_time": None
        }
        self.failed_urls.clear()
        self.rate_limiter.reset()
        if self.proxy_manager:
            self.proxy_manager.stats = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0
            }
        self.ua_rotator.reset_stats()
        self.robots_checker.reset_stats()

    def __enter__(self):
        """Context manager entry."""
        self.stats["start_time"] = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stats["end_time"] = time.time()
        self._save_failed_urls()
        return False
