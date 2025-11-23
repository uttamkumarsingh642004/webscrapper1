"""
API scraper for REST endpoints.

Handles JSON/XML APIs with authentication and pagination support.
"""

import requests
from typing import Any, Dict, List, Optional, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import json
import xmltodict

from web_scraper.scrapers.base_scraper import BaseScraper


class APIScraper(BaseScraper):
    """
    Scraper for REST APIs.

    Supports JSON and XML responses, authentication,
    and API-specific pagination.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize API scraper.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config)

        # Session for connection pooling
        self.session = requests.Session()

        # Timeout configuration
        scraping_config = self.config.get("scraping", {})
        self.timeout = scraping_config.get("timeout", 30)

        # Setup authentication
        self._setup_authentication()

        self.logger.info("APIScraper initialized")

    def _setup_authentication(self) -> None:
        """Setup authentication for API requests."""
        auth_config = self.config.get("request", {}).get("auth", {})

        if not auth_config.get("enabled", False):
            return

        auth_type = auth_config.get("type", "").lower()

        if auth_type == "basic":
            username = auth_config.get("username")
            password = auth_config.get("password")
            if username and password:
                self.session.auth = (username, password)
                self.logger.info("Basic authentication configured")

        elif auth_type == "bearer":
            token = auth_config.get("token")
            if token:
                self.session.headers["Authorization"] = f"Bearer {token}"
                self.logger.info("Bearer token authentication configured")

        elif auth_type == "api_key":
            api_key = auth_config.get("api_key")
            header_name = auth_config.get("header_name", "X-API-Key")
            if api_key:
                self.session.headers[header_name] = api_key
                self.logger.info(f"API key authentication configured ({header_name})")

    def scrape(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Scrape data from a single API endpoint.

        Args:
            url: API endpoint URL
            **kwargs: Additional arguments:
                - method: HTTP method (GET, POST, PUT, DELETE)
                - params: Query parameters
                - data: Request body data
                - json_data: JSON request body
                - response_format: Expected response format (json, xml, text)

        Returns:
            Dictionary containing API response data
        """
        # Apply rate limiting
        self.rate_limiter.acquire()

        # Get request parameters
        method = kwargs.get("method", "GET").upper()
        params = kwargs.get("params", {})
        data = kwargs.get("data")
        json_data = kwargs.get("json_data")
        response_format = kwargs.get("response_format", "json")

        # Get headers and proxy
        headers = self._get_headers()

        # Add content type for JSON requests
        if json_data:
            headers["Content-Type"] = "application/json"

        proxy = self._get_proxy()

        self.stats["total_requests"] += 1

        try:
            # Make request
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=headers,
                proxies=proxy,
                timeout=self.timeout,
                allow_redirects=True
            )

            response.raise_for_status()

            # Parse response based on format
            if response_format == "json":
                parsed_data = response.json()
            elif response_format == "xml":
                parsed_data = xmltodict.parse(response.content)
            else:
                parsed_data = response.text

            # Report success
            proxy_url = proxy.get("http") if proxy else None
            self._handle_request_success(url, proxy_url)

            result = {
                "url": url,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "data": parsed_data,
                "success": True
            }

            self.stats["total_items_scraped"] += 1

            return result

        except requests.exceptions.HTTPError as e:
            # Handle HTTP errors
            status_code = e.response.status_code if e.response else None

            proxy_url = proxy.get("http") if proxy else None
            self._handle_request_failure(url, e, proxy_url)

            return {
                "url": url,
                "status_code": status_code,
                "error": str(e),
                "success": False
            }

        except Exception as e:
            proxy_url = proxy.get("http") if proxy else None
            self._handle_request_failure(url, e, proxy_url)

            return {
                "url": url,
                "error": str(e),
                "success": False
            }

    def scrape_multiple(self, urls: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape multiple API endpoints concurrently.

        Args:
            urls: List of API endpoint URLs
            **kwargs: Additional arguments passed to scrape()

        Returns:
            List of dictionaries containing API responses
        """
        results = []

        # Get concurrency settings
        scraping_config = self.config.get("scraping", {})
        max_workers = scraping_config.get("max_workers", 5)
        show_progress = self.config.get("advanced", {}).get("show_progress_bar", True)

        # Sequential scraping
        if max_workers == 1:
            iterator = tqdm(urls, desc="Scraping APIs") if show_progress else urls
            for url in iterator:
                result = self.scrape(url, **kwargs)
                results.append(result)

        # Concurrent scraping
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_url = {executor.submit(self.scrape, url, **kwargs): url for url in urls}

                if show_progress:
                    for future in tqdm(as_completed(future_to_url), total=len(urls), desc="Scraping APIs"):
                        results.append(future.result())
                else:
                    for future in as_completed(future_to_url):
                        results.append(future.result())

        return results

    def scrape_with_pagination(
        self,
        base_url: str,
        pagination_type: str = "page",
        max_pages: Optional[int] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Scrape API with pagination support.

        Args:
            base_url: Base API endpoint URL
            pagination_type: Type of pagination (page, offset, cursor)
            max_pages: Maximum number of pages to scrape
            **kwargs: Additional arguments:
                - page_param: Parameter name for page number (default: 'page')
                - offset_param: Parameter name for offset (default: 'offset')
                - limit_param: Parameter name for limit (default: 'limit')
                - page_size: Items per page (default: 50)
                - cursor_param: Parameter name for cursor (default: 'cursor')
                - next_cursor_path: JSON path to next cursor in response

        Returns:
            List of dictionaries containing all paginated results
        """
        results = []
        page = 1
        offset = 0
        cursor = None
        max_pages = max_pages or self.config.get("scraping", {}).get("max_pages", 10)

        # Get pagination parameters
        page_param = kwargs.get("page_param", "page")
        offset_param = kwargs.get("offset_param", "offset")
        limit_param = kwargs.get("limit_param", "limit")
        page_size = kwargs.get("page_size", 50)
        cursor_param = kwargs.get("cursor_param", "cursor")
        next_cursor_path = kwargs.get("next_cursor_path", "next_cursor")

        self.logger.info(f"Starting API pagination ({pagination_type})")

        while page <= max_pages:
            # Prepare parameters based on pagination type
            params = kwargs.get("params", {}).copy()

            if pagination_type == "page":
                params[page_param] = page
                if limit_param not in params:
                    params[limit_param] = page_size

            elif pagination_type == "offset":
                params[offset_param] = offset
                params[limit_param] = page_size

            elif pagination_type == "cursor":
                if cursor:
                    params[cursor_param] = cursor
                if limit_param not in params:
                    params[limit_param] = page_size

            # Make request
            result = self.scrape(base_url, params=params, **kwargs)

            # Check for errors
            if not result.get("success", False):
                self.logger.warning(f"Pagination stopped at page {page} due to error")
                break

            results.append(result)

            # Check if there's more data
            data = result.get("data", {})

            if pagination_type == "cursor":
                # Get next cursor from response
                cursor = self._get_nested_value(data, next_cursor_path)
                if not cursor:
                    self.logger.info(f"No more pages (cursor)")
                    break

            elif isinstance(data, list):
                # If response is a list and it's empty or smaller than page_size
                if len(data) == 0 or len(data) < page_size:
                    self.logger.info(f"No more pages (empty or partial page)")
                    break

            elif isinstance(data, dict):
                # Check common pagination indicators
                items = data.get("items") or data.get("results") or data.get("data") or []
                if len(items) == 0 or len(items) < page_size:
                    self.logger.info(f"No more pages (empty or partial page)")
                    break

            # Increment page/offset
            page += 1
            offset += page_size

        self.logger.info(f"API pagination complete. Scraped {len(results)} pages")

        return results

    def _get_nested_value(self, data: Dict, path: str, separator: str = ".") -> Any:
        """
        Get value from nested dictionary using dot notation.

        Args:
            data: Dictionary to search
            path: Path to value (e.g., "pagination.next_cursor")
            separator: Path separator

        Returns:
            Value at path or None if not found
        """
        keys = path.split(separator)
        value = data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value

    def __del__(self):
        """Cleanup when scraper is destroyed."""
        if hasattr(self, 'session'):
            self.session.close()
