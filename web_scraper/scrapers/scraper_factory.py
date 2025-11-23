"""
Scraper factory for automatic scraper selection.

Analyzes websites and selects the most appropriate scraper.
"""

import requests
from typing import Any, Dict, Optional
from urllib.parse import urlparse
import re

from web_scraper.scrapers.base_scraper import BaseScraper
from web_scraper.scrapers.static_scraper import StaticScraper
from web_scraper.scrapers.selenium_scraper import SeleniumScraper
from web_scraper.scrapers.playwright_scraper import PlaywrightScraper
from web_scraper.scrapers.api_scraper import APIScraper


class ScraperFactory:
    """
    Factory for creating the appropriate scraper based on URL and content type.

    Automatically detects whether to use static, dynamic, or API scraper.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize scraper factory.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

    def create_scraper(
        self,
        url: str,
        scraper_type: Optional[str] = None,
        force_type: bool = False
    ) -> BaseScraper:
        """
        Create appropriate scraper for the given URL.

        Args:
            url: URL to scrape
            scraper_type: Specific scraper type to use (auto, static, selenium, playwright, api)
            force_type: Whether to force the specified type without detection

        Returns:
            Appropriate scraper instance
        """
        # Get scraper type from config if not specified
        if scraper_type is None:
            scraper_type = self.config.get("scraping", {}).get("scraper_type", "auto")

        # If force_type is True or type is not auto, use specified type
        if force_type or scraper_type != "auto":
            return self._create_by_type(scraper_type)

        # Auto-detect best scraper
        detected_type = self.detect_scraper_type(url)

        return self._create_by_type(detected_type)

    def _create_by_type(self, scraper_type: str) -> BaseScraper:
        """
        Create scraper of specific type.

        Args:
            scraper_type: Scraper type (static, selenium, playwright, api)

        Returns:
            Scraper instance
        """
        scraper_type = scraper_type.lower()

        if scraper_type == "static":
            return StaticScraper(self.config)
        elif scraper_type == "selenium":
            return SeleniumScraper(self.config)
        elif scraper_type == "playwright":
            return PlaywrightScraper(self.config)
        elif scraper_type == "api":
            return APIScraper(self.config)
        else:
            # Default to static
            return StaticScraper(self.config)

    def detect_scraper_type(self, url: str) -> str:
        """
        Detect the best scraper type for the URL.

        Args:
            url: URL to analyze

        Returns:
            Scraper type (static, selenium, playwright, api)
        """
        # Check if it's an API endpoint
        if self._is_api_endpoint(url):
            return "api"

        # Try to fetch page and analyze
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=10
            )

            content_type = response.headers.get("Content-Type", "").lower()

            # Check content type
            if "application/json" in content_type or "application/xml" in content_type:
                return "api"

            # Analyze HTML content
            if "text/html" in content_type:
                html_content = response.text

                # Check for heavy JavaScript usage
                if self._has_heavy_javascript(html_content, url):
                    # Prefer Playwright for modern sites
                    return "playwright"

                # Default to static scraper
                return "static"

            # Default
            return "static"

        except Exception:
            # On error, default to static scraper
            return "static"

    def _is_api_endpoint(self, url: str) -> bool:
        """
        Check if URL is likely an API endpoint.

        Args:
            url: URL to check

        Returns:
            True if likely API, False otherwise
        """
        # Check URL patterns
        api_patterns = [
            r'/api/',
            r'/rest/',
            r'/v\d+/',
            r'/graphql',
            r'\.json$',
            r'\.xml$',
        ]

        for pattern in api_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True

        # Check subdomain
        parsed = urlparse(url)
        if parsed.netloc.startswith('api.'):
            return True

        return False

    def _has_heavy_javascript(self, html: str, url: str) -> bool:
        """
        Detect if page relies heavily on JavaScript.

        Args:
            html: HTML content
            url: Page URL

        Returns:
            True if heavy JavaScript usage detected
        """
        # Common JavaScript framework indicators
        js_frameworks = [
            r'react',
            r'vue\.js',
            r'angular',
            r'next\.js',
            r'nuxt',
            r'gatsby',
            r'svelte',
            r'ember'
        ]

        html_lower = html.lower()

        # Check for framework indicators
        for framework in js_frameworks:
            if re.search(framework, html_lower):
                return True

        # Check for heavy AJAX usage
        ajax_indicators = [
            r'xhr',
            r'fetch\(',
            r'axios',
            r'$.ajax',
            r'$.get',
            r'$.post'
        ]

        for indicator in ajax_indicators:
            if re.search(indicator, html_lower):
                return True

        # Check for single-page application indicators
        spa_indicators = [
            r'<div[^>]+id=["\']root["\']',
            r'<div[^>]+id=["\']app["\']',
            r'__NEXT_DATA__',
            r'__NUXT__',
        ]

        for indicator in spa_indicators:
            if re.search(indicator, html):
                return True

        # Check for minimal static content (indicates dynamic rendering)
        # Remove scripts and styles
        cleaned_html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        cleaned_html = re.sub(r'<style[^>]*>.*?</style>', '', cleaned_html, flags=re.DOTALL | re.IGNORECASE)

        # Check for actual content
        content_tags = len(re.findall(r'<(p|div|article|section|h\d)[^>]*>[^<]+</\1>', cleaned_html, re.IGNORECASE))

        if content_tags < 5:
            # Very little static content, likely dynamic
            return True

        return False

    def get_recommended_scraper_info(self, url: str) -> Dict[str, Any]:
        """
        Get information about recommended scraper for URL.

        Args:
            url: URL to analyze

        Returns:
            Dictionary with scraper recommendation and reasoning
        """
        try:
            detected_type = self.detect_scraper_type(url)

            reasons = []

            if detected_type == "api":
                reasons.append("URL pattern suggests API endpoint")
            elif detected_type == "playwright":
                reasons.append("Heavy JavaScript usage detected")
                reasons.append("Page likely uses modern frameworks")
            elif detected_type == "static":
                reasons.append("Static HTML content detected")
                reasons.append("Minimal JavaScript required")

            return {
                "recommended_scraper": detected_type,
                "reasons": reasons,
                "url": url
            }

        except Exception as e:
            return {
                "recommended_scraper": "static",
                "reasons": ["Error during detection, defaulting to static"],
                "error": str(e),
                "url": url
            }


def create_scraper(
    url: Optional[str] = None,
    scraper_type: str = "auto",
    config: Optional[Dict[str, Any]] = None
) -> BaseScraper:
    """
    Convenience function to create a scraper.

    Args:
        url: URL to scrape (required for auto-detection)
        scraper_type: Scraper type (auto, static, selenium, playwright, api)
        config: Configuration dictionary

    Returns:
        Scraper instance
    """
    factory = ScraperFactory(config)

    if scraper_type == "auto" and url:
        return factory.create_scraper(url, scraper_type=scraper_type)
    else:
        return factory._create_by_type(scraper_type if scraper_type != "auto" else "static")
