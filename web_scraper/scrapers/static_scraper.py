"""
Static HTML scraper using BeautifulSoup and requests.

Handles static HTML pages with CSS selectors, XPath, and regex patterns.
"""

import re
import requests
from typing import Any, Dict, List, Optional, Union
from bs4 import BeautifulSoup
from lxml import html as lxml_html, etree
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from web_scraper.scrapers.base_scraper import BaseScraper


class StaticScraper(BaseScraper):
    """
    Scraper for static HTML content.

    Uses requests for fetching and BeautifulSoup/lxml for parsing.
    Supports CSS selectors, XPath, and regex extraction.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize static scraper.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config)

        # Session for connection pooling
        self.session = requests.Session()

        # Timeout configuration
        scraping_config = self.config.get("scraping", {})
        self.timeout = scraping_config.get("timeout", 30)

        # Parser preference
        self.parser = "lxml"  # Can be: lxml, html.parser, html5lib

        self.logger.info("StaticScraper initialized")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError))
    )
    def _fetch_page(self, url: str) -> requests.Response:
        """
        Fetch a page with retry logic.

        Args:
            url: URL to fetch

        Returns:
            Response object

        Raises:
            requests.RequestException: If request fails after retries
        """
        # Apply rate limiting
        self.rate_limiter.acquire()

        # Check robots.txt
        if not self._check_robots_txt(url):
            raise PermissionError(f"Robots.txt disallows scraping: {url}")

        # Get headers and proxy
        headers = self._get_headers()
        proxy = self._get_proxy()

        self.stats["total_requests"] += 1

        try:
            response = self.session.get(
                url,
                headers=headers,
                proxies=proxy,
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()

            # Report success
            proxy_url = proxy.get("http") if proxy else None
            self._handle_request_success(url, proxy_url)

            return response

        except requests.RequestException as e:
            # Report failure
            proxy_url = proxy.get("http") if proxy else None
            self._handle_request_failure(url, e, proxy_url)
            raise

    def scrape(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Scrape data from a single URL.

        Args:
            url: URL to scrape
            **kwargs: Additional arguments:
                - selectors: Dict of CSS selectors
                - xpath_selectors: Dict of XPath selectors
                - regex_patterns: Dict of regex patterns
                - extract_all: Whether to extract all matches (default: False)

        Returns:
            Dictionary containing scraped data
        """
        try:
            response = self._fetch_page(url)

            # Parse HTML
            soup = BeautifulSoup(response.content, self.parser)
            tree = lxml_html.fromstring(response.content)

            # Extract data
            data = {
                "url": url,
                "status_code": response.status_code,
                "content_type": response.headers.get("Content-Type", ""),
                "html": response.text
            }

            # Extract using CSS selectors
            selectors = kwargs.get("selectors") or self.config.get("extraction", {}).get("css_selectors", {})
            if selectors:
                data["extracted_data"] = self._extract_with_css(soup, selectors, kwargs.get("extract_all", False))

            # Extract using XPath
            xpath_selectors = kwargs.get("xpath_selectors") or self.config.get("extraction", {}).get("xpath_selectors", {})
            if xpath_selectors:
                xpath_data = self._extract_with_xpath(tree, xpath_selectors, kwargs.get("extract_all", False))
                if "extracted_data" in data:
                    data["extracted_data"].update(xpath_data)
                else:
                    data["extracted_data"] = xpath_data

            # Extract using regex
            regex_patterns = kwargs.get("regex_patterns") or self.config.get("extraction", {}).get("regex_patterns", {})
            if regex_patterns:
                regex_data = self._extract_with_regex(response.text, regex_patterns, kwargs.get("extract_all", False))
                if "extracted_data" in data:
                    data["extracted_data"].update(regex_data)
                else:
                    data["extracted_data"] = regex_data

            self.stats["total_items_scraped"] += 1

            return data

        except Exception as e:
            self.logger.error(f"Error scraping {url}: {e}")
            return {
                "url": url,
                "error": str(e),
                "success": False
            }

    def _extract_with_css(self, soup: BeautifulSoup, selectors: Dict[str, str], extract_all: bool = False) -> Dict[str, Any]:
        """
        Extract data using CSS selectors.

        Args:
            soup: BeautifulSoup object
            selectors: Dictionary of field_name: selector pairs
            extract_all: Whether to extract all matches

        Returns:
            Dictionary of extracted data
        """
        data = {}

        for field, selector in selectors.items():
            try:
                if extract_all:
                    elements = soup.select(selector)
                    data[field] = [self._extract_element_data(el) for el in elements]
                else:
                    element = soup.select_one(selector)
                    data[field] = self._extract_element_data(element) if element else None

            except Exception as e:
                self.logger.warning(f"Error extracting '{field}' with selector '{selector}': {e}")
                data[field] = None

        return data

    def _extract_with_xpath(self, tree: etree._Element, selectors: Dict[str, str], extract_all: bool = False) -> Dict[str, Any]:
        """
        Extract data using XPath selectors.

        Args:
            tree: lxml tree object
            selectors: Dictionary of field_name: xpath pairs
            extract_all: Whether to extract all matches

        Returns:
            Dictionary of extracted data
        """
        data = {}

        for field, xpath in selectors.items():
            try:
                elements = tree.xpath(xpath)

                if not elements:
                    data[field] = None
                elif extract_all:
                    data[field] = [self._extract_xpath_element(el) for el in elements]
                else:
                    data[field] = self._extract_xpath_element(elements[0])

            except Exception as e:
                self.logger.warning(f"Error extracting '{field}' with XPath '{xpath}': {e}")
                data[field] = None

        return data

    def _extract_with_regex(self, text: str, patterns: Dict[str, str], extract_all: bool = False) -> Dict[str, Any]:
        """
        Extract data using regex patterns.

        Args:
            text: Text to search
            patterns: Dictionary of field_name: pattern pairs
            extract_all: Whether to extract all matches

        Returns:
            Dictionary of extracted data
        """
        data = {}

        for field, pattern in patterns.items():
            try:
                if extract_all:
                    matches = re.findall(pattern, text)
                    data[field] = matches if matches else None
                else:
                    match = re.search(pattern, text)
                    data[field] = match.group(1) if match and match.groups() else (match.group(0) if match else None)

            except Exception as e:
                self.logger.warning(f"Error extracting '{field}' with regex '{pattern}': {e}")
                data[field] = None

        return data

    def _extract_element_data(self, element) -> Optional[str]:
        """
        Extract data from a BeautifulSoup element.

        Args:
            element: BeautifulSoup element

        Returns:
            Extracted text or None
        """
        if element is None:
            return None

        # Try to get text content
        text = element.get_text(strip=True)

        # Clean whitespace if configured
        if self.config.get("extraction", {}).get("clean_whitespace", True):
            text = " ".join(text.split())

        return text if text else None

    def _extract_xpath_element(self, element) -> Optional[str]:
        """
        Extract data from an lxml element.

        Args:
            element: lxml element

        Returns:
            Extracted text or None
        """
        if isinstance(element, str):
            return element

        if hasattr(element, 'text_content'):
            text = element.text_content().strip()
        elif hasattr(element, 'text'):
            text = element.text.strip() if element.text else ""
        else:
            text = str(element).strip()

        # Clean whitespace if configured
        if self.config.get("extraction", {}).get("clean_whitespace", True):
            text = " ".join(text.split())

        return text if text else None

    def scrape_multiple(self, urls: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs concurrently.

        Args:
            urls: List of URLs to scrape
            **kwargs: Additional arguments passed to scrape()

        Returns:
            List of dictionaries containing scraped data
        """
        results = []

        # Get concurrency settings
        scraping_config = self.config.get("scraping", {})
        max_workers = scraping_config.get("max_workers", 5)
        show_progress = self.config.get("advanced", {}).get("show_progress_bar", True)

        # Sequential scraping (with optional progress bar)
        if max_workers == 1:
            iterator = tqdm(urls, desc="Scraping") if show_progress else urls
            for url in iterator:
                result = self.scrape(url, **kwargs)
                results.append(result)

        # Concurrent scraping
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_url = {executor.submit(self.scrape, url, **kwargs): url for url in urls}

                # With progress bar
                if show_progress:
                    for future in tqdm(as_completed(future_to_url), total=len(urls), desc="Scraping"):
                        results.append(future.result())
                # Without progress bar
                else:
                    for future in as_completed(future_to_url):
                        results.append(future.result())

        return results

    def scrape_with_pagination(
        self,
        base_url: str,
        page_param: str = "page",
        start_page: int = 1,
        max_pages: Optional[int] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple pages with numbered pagination.

        Args:
            base_url: Base URL (without page parameter)
            page_param: URL parameter name for page number
            start_page: Starting page number
            max_pages: Maximum number of pages to scrape
            **kwargs: Additional arguments passed to scrape()

        Returns:
            List of dictionaries containing scraped data
        """
        results = []
        page = start_page
        max_pages = max_pages or self.config.get("scraping", {}).get("max_pages", 10)

        self.logger.info(f"Starting pagination scraping from page {start_page}")

        while page < start_page + max_pages:
            # Construct URL
            separator = "&" if "?" in base_url else "?"
            url = f"{base_url}{separator}{page_param}={page}"

            self.logger.debug(f"Scraping page {page}: {url}")

            try:
                result = self.scrape(url, **kwargs)

                # Check if page is empty or has no data
                if not result or result.get("error"):
                    self.logger.info(f"Stopping pagination at page {page} (error or empty)")
                    break

                results.append(result)
                page += 1

            except Exception as e:
                self.logger.error(f"Error scraping page {page}: {e}")
                break

        self.logger.info(f"Pagination complete. Scraped {len(results)} pages")

        return results

    def __del__(self):
        """Cleanup when scraper is destroyed."""
        if hasattr(self, 'session'):
            self.session.close()
