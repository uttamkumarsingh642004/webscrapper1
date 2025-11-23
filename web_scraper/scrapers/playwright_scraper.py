"""
Dynamic content scraper using Playwright.

Modern alternative to Selenium with better performance and features.
"""

import time
from typing import Any, Dict, List, Optional
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from tqdm import tqdm

from web_scraper.scrapers.base_scraper import BaseScraper


class PlaywrightScraper(BaseScraper):
    """
    Scraper for dynamic content using Playwright.

    Offers modern browser automation with excellent performance
    and support for multiple browser engines.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Playwright scraper.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config)

        # Browser configuration
        scraping_config = self.config.get("scraping", {})
        self.browser_type = scraping_config.get("browser", "chromium").lower()
        self.headless = scraping_config.get("headless", True)
        self.page_load_timeout = scraping_config.get("page_load_timeout", 60) * 1000  # Convert to ms

        # Advanced configuration
        advanced_config = self.config.get("advanced", {})
        self.take_screenshots = advanced_config.get("take_screenshots", False)
        self.screenshot_dir = advanced_config.get("screenshot_dir", "screenshots")
        self.screenshot_on_error = advanced_config.get("screenshot_on_error", False)

        self.playwright = None
        self.browser = None

        self.logger.info(f"PlaywrightScraper initialized with {self.browser_type} browser")

    def _init_browser(self) -> None:
        """Initialize Playwright browser."""
        if self.playwright is None:
            self.playwright = sync_playwright().start()

            # Select browser
            if self.browser_type == "chromium":
                browser_launcher = self.playwright.chromium
            elif self.browser_type == "firefox":
                browser_launcher = self.playwright.firefox
            elif self.browser_type == "webkit":
                browser_launcher = self.playwright.webkit
            else:
                raise ValueError(f"Unsupported browser: {self.browser_type}")

            # Launch browser
            self.browser = browser_launcher.launch(headless=self.headless)

    def _create_context(self) -> BrowserContext:
        """
        Create new browser context.

        Returns:
            BrowserContext instance
        """
        self._init_browser()

        # Get user agent
        user_agent = self.ua_rotator.get_random_user_agent()

        # Create context with custom settings
        context = self.browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1920, "height": 1080},
            accept_downloads=False
        )

        context.set_default_timeout(self.page_load_timeout)

        return context

    def scrape(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Scrape data from a single URL.

        Args:
            url: URL to scrape
            **kwargs: Additional arguments:
                - wait_for_selector: CSS selector to wait for
                - wait_timeout: Timeout for waiting (ms)
                - wait_for_load_state: Load state to wait for (load, domcontentloaded, networkidle)
                - execute_script: JavaScript to execute
                - click_selectors: List of selectors to click
                - scroll_to_bottom: Whether to scroll to bottom

        Returns:
            Dictionary containing scraped data
        """
        context = None
        page = None

        try:
            # Apply rate limiting
            self.rate_limiter.acquire()

            # Check robots.txt
            if not self._check_robots_txt(url):
                raise PermissionError(f"Robots.txt disallows scraping: {url}")

            # Create context and page
            context = self._create_context()
            page = context.new_page()

            self.stats["total_requests"] += 1

            # Navigate to URL
            self.logger.debug(f"Navigating to {url}")
            response = page.goto(url, wait_until=kwargs.get("wait_for_load_state", "load"))

            # Wait for specific selector if provided
            wait_for = kwargs.get("wait_for_selector")
            if wait_for:
                wait_timeout = kwargs.get("wait_timeout", 10000)
                try:
                    page.wait_for_selector(wait_for, timeout=wait_timeout)
                except PlaywrightTimeout:
                    self.logger.warning(f"Timeout waiting for selector: {wait_for}")

            # Execute custom JavaScript
            script = kwargs.get("execute_script")
            if script:
                page.evaluate(script)
                time.sleep(1)

            # Click elements if specified
            click_selectors = kwargs.get("click_selectors", [])
            for selector in click_selectors:
                try:
                    page.click(selector)
                    time.sleep(1)
                except Exception as e:
                    self.logger.warning(f"Failed to click selector '{selector}': {e}")

            # Scroll to bottom if requested
            if kwargs.get("scroll_to_bottom", False):
                self._scroll_to_bottom(page)

            # Get page content
            page_content = page.content()
            current_url = page.url

            # Parse with BeautifulSoup
            soup = BeautifulSoup(page_content, "lxml")

            # Extract data
            data = {
                "url": url,
                "final_url": current_url,
                "title": page.title(),
                "html": page_content,
                "status_code": response.status if response else None
            }

            # Extract using CSS selectors
            selectors = kwargs.get("selectors") or self.config.get("extraction", {}).get("css_selectors", {})
            if selectors:
                from web_scraper.scrapers.static_scraper import StaticScraper
                static_scraper = StaticScraper(self.config)
                data["extracted_data"] = static_scraper._extract_with_css(soup, selectors, kwargs.get("extract_all", False))

            # Take screenshot if enabled
            if self.take_screenshots:
                self._take_screenshot(page, url)

            self._handle_request_success(url)
            self.stats["total_items_scraped"] += 1

            return data

        except Exception as e:
            self.logger.error(f"Error scraping {url}: {e}")

            # Take screenshot on error
            if page and self.screenshot_on_error:
                try:
                    self._take_screenshot(page, url, suffix="_error")
                except:
                    pass

            self._handle_request_failure(url, e)

            return {
                "url": url,
                "error": str(e),
                "success": False
            }

        finally:
            if page:
                page.close()
            if context:
                context.close()

    def _scroll_to_bottom(self, page: Page, pause_time: float = 2.0) -> None:
        """
        Scroll to bottom of page to load dynamic content.

        Args:
            page: Playwright Page instance
            pause_time: Time to pause between scrolls
        """
        last_height = page.evaluate("document.body.scrollHeight")

        while True:
            # Scroll down
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(pause_time)

            # Calculate new height
            new_height = page.evaluate("document.body.scrollHeight")

            # Break if no more content
            if new_height == last_height:
                break

            last_height = new_height

    def _take_screenshot(self, page: Page, url: str, suffix: str = "") -> None:
        """
        Take screenshot of current page.

        Args:
            page: Playwright Page instance
            url: URL being scraped
            suffix: Suffix for filename
        """
        try:
            from pathlib import Path
            import hashlib

            screenshot_dir = Path(self.screenshot_dir)
            screenshot_dir.mkdir(parents=True, exist_ok=True)

            # Create filename from URL hash
            url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
            filename = screenshot_dir / f"screenshot_{url_hash}{suffix}.png"

            page.screenshot(path=str(filename), full_page=True)
            self.logger.info(f"Screenshot saved: {filename}")

        except Exception as e:
            self.logger.warning(f"Failed to save screenshot: {e}")

    def scrape_multiple(self, urls: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs.

        Args:
            urls: List of URLs to scrape
            **kwargs: Additional arguments passed to scrape()

        Returns:
            List of dictionaries containing scraped data
        """
        results = []

        # Get settings
        show_progress = self.config.get("advanced", {}).get("show_progress_bar", True)

        # Playwright is single-threaded, so we scrape sequentially
        iterator = tqdm(urls, desc="Scraping") if show_progress else urls

        for url in iterator:
            result = self.scrape(url, **kwargs)
            results.append(result)

        return results

    def scrape_with_infinite_scroll(
        self,
        url: str,
        max_scrolls: int = 10,
        pause_time: float = 2.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Scrape page with infinite scroll.

        Args:
            url: URL to scrape
            max_scrolls: Maximum number of scrolls
            pause_time: Time to pause between scrolls
            **kwargs: Additional arguments

        Returns:
            Dictionary containing scraped data
        """
        context = None
        page = None

        try:
            context = self._create_context()
            page = context.new_page()

            page.goto(url)

            # Scroll multiple times
            for i in range(max_scrolls):
                last_height = page.evaluate("document.body.scrollHeight")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(pause_time)

                new_height = page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    self.logger.info(f"Reached end of scroll at iteration {i}")
                    break

            # Get final page content
            page_content = page.content()
            soup = BeautifulSoup(page_content, "lxml")

            data = {
                "url": url,
                "html": page_content,
                "title": page.title()
            }

            # Extract data
            selectors = kwargs.get("selectors") or self.config.get("extraction", {}).get("css_selectors", {})
            if selectors:
                from web_scraper.scrapers.static_scraper import StaticScraper
                static_scraper = StaticScraper(self.config)
                data["extracted_data"] = static_scraper._extract_with_css(soup, selectors, kwargs.get("extract_all", True))

            return data

        finally:
            if page:
                page.close()
            if context:
                context.close()

    def __del__(self):
        """Cleanup when scraper is destroyed."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
