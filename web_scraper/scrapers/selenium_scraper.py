"""
Dynamic content scraper using Selenium.

Handles JavaScript-heavy sites with Selenium WebDriver.
"""

import time
from typing import Any, Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from web_scraper.scrapers.base_scraper import BaseScraper


class SeleniumScraper(BaseScraper):
    """
    Scraper for dynamic content using Selenium.

    Handles JavaScript rendering, AJAX requests, and dynamic content loading.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Selenium scraper.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config)

        # Browser configuration
        scraping_config = self.config.get("scraping", {})
        self.browser = scraping_config.get("browser", "chrome").lower()
        self.headless = scraping_config.get("headless", True)
        self.page_load_timeout = scraping_config.get("page_load_timeout", 60)

        # AJAX configuration
        advanced_config = self.config.get("advanced", {})
        self.detect_ajax = advanced_config.get("detect_ajax", True)
        self.ajax_wait_time = advanced_config.get("ajax_wait_time", 5)

        # Screenshot configuration
        self.take_screenshots = advanced_config.get("take_screenshots", False)
        self.screenshot_dir = advanced_config.get("screenshot_dir", "screenshots")
        self.screenshot_on_error = advanced_config.get("screenshot_on_error", False)

        # Driver pool for concurrent scraping
        self.driver_pool: List[webdriver.Remote] = []

        self.logger.info(f"SeleniumScraper initialized with {self.browser} browser")

    def _create_driver(self) -> webdriver.Remote:
        """
        Create a new WebDriver instance.

        Returns:
            WebDriver instance
        """
        try:
            if self.browser == "chrome":
                options = ChromeOptions()
                if self.headless:
                    options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")

                # Add user agent
                user_agent = self.ua_rotator.get_chrome()
                options.add_argument(f"user-agent={user_agent}")

                service = ChromeService(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)

            elif self.browser == "firefox":
                options = FirefoxOptions()
                if self.headless:
                    options.add_argument("--headless")
                options.add_argument("--width=1920")
                options.add_argument("--height=1080")

                # Add user agent
                user_agent = self.ua_rotator.get_firefox()
                options.set_preference("general.useragent.override", user_agent)

                service = FirefoxService(GeckoDriverManager().install())
                driver = webdriver.Firefox(service=service, options=options)

            else:
                raise ValueError(f"Unsupported browser: {self.browser}")

            driver.set_page_load_timeout(self.page_load_timeout)

            return driver

        except Exception as e:
            self.logger.error(f"Failed to create WebDriver: {e}")
            raise

    def _wait_for_page_load(self, driver: webdriver.Remote, timeout: Optional[int] = None) -> None:
        """
        Wait for page to fully load.

        Args:
            driver: WebDriver instance
            timeout: Timeout in seconds
        """
        timeout = timeout or self.page_load_timeout

        try:
            # Wait for document ready state
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # Wait for AJAX if enabled
            if self.detect_ajax:
                time.sleep(self.ajax_wait_time)
                # Wait for jQuery if present
                try:
                    WebDriverWait(driver, 5).until(
                        lambda d: d.execute_script("return typeof jQuery != 'undefined' ? jQuery.active == 0 : true")
                    )
                except:
                    pass  # jQuery not present

        except TimeoutException:
            self.logger.warning(f"Page load timeout after {timeout} seconds")

    def scrape(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Scrape data from a single URL.

        Args:
            url: URL to scrape
            **kwargs: Additional arguments:
                - wait_for_selector: CSS selector to wait for
                - wait_timeout: Timeout for waiting
                - scroll_to_bottom: Whether to scroll to page bottom
                - execute_script: JavaScript to execute
                - click_selectors: List of selectors to click

        Returns:
            Dictionary containing scraped data
        """
        driver = None

        try:
            # Apply rate limiting
            self.rate_limiter.acquire()

            # Check robots.txt
            if not self._check_robots_txt(url):
                raise PermissionError(f"Robots.txt disallows scraping: {url}")

            # Create driver
            driver = self._create_driver()

            self.stats["total_requests"] += 1

            # Navigate to URL
            self.logger.debug(f"Navigating to {url}")
            driver.get(url)

            # Wait for page load
            self._wait_for_page_load(driver)

            # Wait for specific selector if provided
            wait_for = kwargs.get("wait_for_selector")
            if wait_for:
                wait_timeout = kwargs.get("wait_timeout", 10)
                try:
                    WebDriverWait(driver, wait_timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
                    )
                except TimeoutException:
                    self.logger.warning(f"Timeout waiting for selector: {wait_for}")

            # Execute custom JavaScript
            script = kwargs.get("execute_script")
            if script:
                driver.execute_script(script)
                time.sleep(1)

            # Click elements if specified
            click_selectors = kwargs.get("click_selectors", [])
            for selector in click_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    element.click()
                    time.sleep(1)
                except Exception as e:
                    self.logger.warning(f"Failed to click selector '{selector}': {e}")

            # Scroll to bottom if requested
            if kwargs.get("scroll_to_bottom", False):
                self._scroll_to_bottom(driver)

            # Get page source
            page_source = driver.page_source
            current_url = driver.current_url

            # Parse with BeautifulSoup
            soup = BeautifulSoup(page_source, "lxml")

            # Extract data
            data = {
                "url": url,
                "final_url": current_url,
                "title": driver.title,
                "html": page_source
            }

            # Extract using CSS selectors
            selectors = kwargs.get("selectors") or self.config.get("extraction", {}).get("css_selectors", {})
            if selectors:
                from web_scraper.scrapers.static_scraper import StaticScraper
                static_scraper = StaticScraper(self.config)
                data["extracted_data"] = static_scraper._extract_with_css(soup, selectors, kwargs.get("extract_all", False))

            # Take screenshot if enabled
            if self.take_screenshots:
                self._take_screenshot(driver, url)

            self._handle_request_success(url)
            self.stats["total_items_scraped"] += 1

            return data

        except Exception as e:
            self.logger.error(f"Error scraping {url}: {e}")

            # Take screenshot on error
            if driver and self.screenshot_on_error:
                try:
                    self._take_screenshot(driver, url, suffix="_error")
                except:
                    pass

            self._handle_request_failure(url, e)

            return {
                "url": url,
                "error": str(e),
                "success": False
            }

        finally:
            if driver:
                driver.quit()

    def _scroll_to_bottom(self, driver: webdriver.Remote, pause_time: float = 2.0) -> None:
        """
        Scroll to bottom of page to load dynamic content.

        Args:
            driver: WebDriver instance
            pause_time: Time to pause between scrolls
        """
        last_height = driver.execute_script("return document.body.scrollHeight")

        while True:
            # Scroll down
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause_time)

            # Calculate new height
            new_height = driver.execute_script("return document.body.scrollHeight")

            # Break if no more content
            if new_height == last_height:
                break

            last_height = new_height

    def _take_screenshot(self, driver: webdriver.Remote, url: str, suffix: str = "") -> None:
        """
        Take screenshot of current page.

        Args:
            driver: WebDriver instance
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

            driver.save_screenshot(str(filename))
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

        # Get concurrency settings
        scraping_config = self.config.get("scraping", {})
        max_workers = scraping_config.get("max_workers", 1)  # Default to 1 for Selenium
        show_progress = self.config.get("advanced", {}).get("show_progress_bar", True)

        # Sequential scraping (recommended for Selenium)
        if max_workers == 1:
            iterator = tqdm(urls, desc="Scraping") if show_progress else urls
            for url in iterator:
                result = self.scrape(url, **kwargs)
                results.append(result)

        # Concurrent scraping (use with caution - resource intensive)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_url = {executor.submit(self.scrape, url, **kwargs): url for url in urls}

                if show_progress:
                    for future in tqdm(as_completed(future_to_url), total=len(urls), desc="Scraping"):
                        results.append(future.result())
                else:
                    for future in as_completed(future_to_url):
                        results.append(future.result())

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
        driver = None

        try:
            driver = self._create_driver()
            driver.get(url)
            self._wait_for_page_load(driver)

            # Scroll multiple times
            for i in range(max_scrolls):
                last_height = driver.execute_script("return document.body.scrollHeight")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(pause_time)

                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    self.logger.info(f"Reached end of scroll at iteration {i}")
                    break

            # Get final page source
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "lxml")

            data = {
                "url": url,
                "html": page_source,
                "title": driver.title
            }

            # Extract data
            selectors = kwargs.get("selectors") or self.config.get("extraction", {}).get("css_selectors", {})
            if selectors:
                from web_scraper.scrapers.static_scraper import StaticScraper
                static_scraper = StaticScraper(self.config)
                data["extracted_data"] = static_scraper._extract_with_css(soup, selectors, kwargs.get("extract_all", True))

            return data

        finally:
            if driver:
                driver.quit()
