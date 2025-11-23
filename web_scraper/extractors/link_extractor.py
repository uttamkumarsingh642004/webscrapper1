"""
Link extraction utilities.

Provides methods to extract and classify links from HTML.
"""

from typing import List, Dict, Optional, Set, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
import re


class LinkExtractor:
    """
    Extract and analyze links from HTML content.

    Handles internal/external links, categorization, and filtering.
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize link extractor.

        Args:
            base_url: Base URL for resolving relative URLs
        """
        self.base_url = base_url

    def extract_links(self, html: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract all links from HTML.

        Args:
            html: HTML content
            base_url: Base URL for resolving relative URLs

        Returns:
            List of dictionaries containing link data
        """
        soup = BeautifulSoup(html, "lxml")
        base_url = base_url or self.base_url

        links = []

        for tag in soup.find_all("a", href=True):
            link_data = self._extract_link_data(tag, base_url)
            if link_data:
                links.append(link_data)

        return links

    def extract_link_urls(self, html: str, base_url: Optional[str] = None, unique: bool = True) -> List[str]:
        """
        Extract just the link URLs.

        Args:
            html: HTML content
            base_url: Base URL for resolving relative URLs
            unique: Whether to return unique URLs only

        Returns:
            List of link URLs
        """
        links = self.extract_links(html, base_url)
        urls = [link["href"] for link in links if link.get("href")]

        if unique:
            # Preserve order while removing duplicates
            seen = set()
            unique_urls = []
            for url in urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)
            return unique_urls

        return urls

    def _extract_link_data(self, tag, base_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Extract data from link tag.

        Args:
            tag: BeautifulSoup anchor tag
            base_url: Base URL for resolving relative URLs

        Returns:
            Dictionary with link data
        """
        href = tag.get("href", "").strip()

        if not href:
            return None

        # Resolve relative URLs
        absolute_url = urljoin(base_url, href) if base_url else href

        # Parse URL
        parsed = urlparse(absolute_url)

        link_data = {
            "href": absolute_url,
            "text": tag.get_text(strip=True),
            "title": tag.get("title", ""),
            "rel": tag.get("rel", []),
            "target": tag.get("target"),
            "class": tag.get("class", []),
            "id": tag.get("id"),
            "domain": parsed.netloc,
            "path": parsed.path,
            "scheme": parsed.scheme,
            "fragment": parsed.fragment
        }

        # Classify link type
        if base_url:
            link_data["is_internal"] = self._is_internal_link(absolute_url, base_url)
            link_data["is_external"] = not link_data["is_internal"]

        # Extract query parameters
        if parsed.query:
            link_data["query_params"] = parse_qs(parsed.query)

        # Identify special link types
        link_data["link_type"] = self._classify_link_type(absolute_url, tag)

        return link_data

    def _is_internal_link(self, url: str, base_url: str) -> bool:
        """
        Check if link is internal.

        Args:
            url: URL to check
            base_url: Base URL of the site

        Returns:
            True if internal, False otherwise
        """
        parsed_url = urlparse(url)
        parsed_base = urlparse(base_url)

        # Compare domains
        return parsed_url.netloc == parsed_base.netloc or parsed_url.netloc == ""

    def _classify_link_type(self, url: str, tag) -> str:
        """
        Classify the type of link.

        Args:
            url: Link URL
            tag: Link tag

        Returns:
            Link type string
        """
        url_lower = url.lower()

        # Email
        if url.startswith("mailto:"):
            return "email"

        # Telephone
        if url.startswith("tel:"):
            return "telephone"

        # File download
        download_extensions = [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.rar', '.tar', '.gz', '.7z',
            '.exe', '.dmg', '.pkg', '.deb', '.rpm'
        ]
        if any(url_lower.endswith(ext) for ext in download_extensions):
            return "download"

        # Image
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.bmp', '.ico']
        if any(url_lower.endswith(ext) for ext in image_extensions):
            return "image"

        # Video
        video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv']
        if any(url_lower.endswith(ext) for ext in video_extensions):
            return "video"

        # Social media
        social_domains = [
            'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
            'youtube.com', 'tiktok.com', 'pinterest.com', 'reddit.com'
        ]
        if any(domain in url_lower for domain in social_domains):
            return "social"

        # JavaScript
        if url.startswith("javascript:"):
            return "javascript"

        # Anchor (same page)
        if url.startswith("#"):
            return "anchor"

        # Default to page
        return "page"

    def filter_internal_links(self, html: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract only internal links.

        Args:
            html: HTML content
            base_url: Base URL

        Returns:
            List of internal links
        """
        links = self.extract_links(html, base_url)
        return [link for link in links if link.get("is_internal", False)]

    def filter_external_links(self, html: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract only external links.

        Args:
            html: HTML content
            base_url: Base URL

        Returns:
            List of external links
        """
        links = self.extract_links(html, base_url)
        return [link for link in links if link.get("is_external", False)]

    def extract_by_selector(self, html: str, selector: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract links matching CSS selector.

        Args:
            html: HTML content
            selector: CSS selector
            base_url: Base URL

        Returns:
            List of links
        """
        soup = BeautifulSoup(html, "lxml")
        base_url = base_url or self.base_url

        links = []
        for element in soup.select(selector):
            if element.name == "a" and element.get("href"):
                link_data = self._extract_link_data(element, base_url)
                if link_data:
                    links.append(link_data)

        return links

    def extract_navigation_links(self, html: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract navigation links.

        Args:
            html: HTML content
            base_url: Base URL

        Returns:
            List of navigation links
        """
        soup = BeautifulSoup(html, "lxml")

        # Common navigation selectors
        nav_selectors = [
            "nav a",
            "header a",
            ".nav a",
            ".navigation a",
            ".menu a",
            "#nav a",
            "#navigation a",
            "#menu a",
            '[role="navigation"] a'
        ]

        nav_links = []
        seen_urls = set()

        for selector in nav_selectors:
            links = self.extract_by_selector(html, selector, base_url)
            for link in links:
                if link["href"] not in seen_urls:
                    nav_links.append(link)
                    seen_urls.add(link["href"])

        return nav_links

    def extract_pagination_links(self, html: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract pagination links.

        Args:
            html: HTML content
            base_url: Base URL

        Returns:
            List of pagination links
        """
        soup = BeautifulSoup(html, "lxml")

        # Common pagination selectors
        pagination_selectors = [
            ".pagination a",
            ".pager a",
            ".page-numbers a",
            '[role="navigation"][aria-label*="pagination"] a',
            'nav[aria-label*="pagination"] a'
        ]

        pagination_links = []
        seen_urls = set()

        for selector in pagination_selectors:
            links = self.extract_by_selector(html, selector, base_url)
            for link in links:
                if link["href"] not in seen_urls:
                    pagination_links.append(link)
                    seen_urls.add(link["href"])

        return pagination_links

    def extract_next_page_link(self, html: str, base_url: Optional[str] = None) -> Optional[str]:
        """
        Extract next page link from pagination.

        Args:
            html: HTML content
            base_url: Base URL

        Returns:
            Next page URL or None
        """
        soup = BeautifulSoup(html, "lxml")

        # Common next page selectors
        next_selectors = [
            'a[rel="next"]',
            'a.next',
            'a.next-page',
            '.pagination a:contains("Next")',
            '.pager a:contains("Next")',
            'a[aria-label="Next"]'
        ]

        for selector in next_selectors:
            # Use simple find for most selectors
            if ':contains' in selector:
                continue

            element = soup.select_one(selector)
            if element and element.get("href"):
                url = element["href"]
                return urljoin(base_url, url) if base_url else url

        # Text-based search for "Next"
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True).lower()
            if text in ["next", "next page", "→", "»", ">"]:
                url = link["href"]
                return urljoin(base_url, url) if base_url else url

        return None

    def group_links_by_domain(self, links: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group links by domain.

        Args:
            links: List of link dictionaries

        Returns:
            Dictionary mapping domains to lists of links
        """
        grouped = {}

        for link in links:
            domain = link.get("domain", "unknown")
            if domain not in grouped:
                grouped[domain] = []
            grouped[domain].append(link)

        return grouped

    def get_broken_link_candidates(self, links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get links that might be broken.

        Args:
            links: List of link dictionaries

        Returns:
            List of potentially broken links
        """
        broken_candidates = []

        for link in links:
            href = link.get("href", "")

            # Empty href
            if not href or href == "#":
                continue

            # JavaScript links
            if href.startswith("javascript:"):
                continue

            # Suspicious patterns
            suspicious_patterns = [
                r'localhost',
                r'127\.0\.0\.1',
                r'0\.0\.0\.0',
                r'example\.com',
                r'test\.com',
                r'\.local',
            ]

            if any(re.search(pattern, href, re.IGNORECASE) for pattern in suspicious_patterns):
                broken_candidates.append(link)

        return broken_candidates
