"""
Image extraction utilities.

Provides methods to extract image URLs and metadata from HTML.
"""

import re
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import base64


class ImageExtractor:
    """
    Extract images and their metadata from HTML.

    Handles various image formats, sources, and attributes.
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize image extractor.

        Args:
            base_url: Base URL for resolving relative URLs
        """
        self.base_url = base_url

    def extract_images(self, html: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract all images from HTML.

        Args:
            html: HTML content
            base_url: Base URL for resolving relative URLs

        Returns:
            List of dictionaries containing image data
        """
        soup = BeautifulSoup(html, "lxml")
        base_url = base_url or self.base_url

        images = []

        # Extract <img> tags
        for img in soup.find_all("img"):
            image_data = self._extract_img_data(img, base_url)
            if image_data:
                images.append(image_data)

        # Extract images from CSS backgrounds
        for element in soup.find_all(style=re.compile(r'background-image')):
            image_data = self._extract_css_background(element, base_url)
            if image_data:
                images.append(image_data)

        # Extract <picture> elements
        for picture in soup.find_all("picture"):
            image_data = self._extract_picture_data(picture, base_url)
            if image_data:
                images.extend(image_data)

        return images

    def extract_image_urls(self, html: str, base_url: Optional[str] = None) -> List[str]:
        """
        Extract just the image URLs.

        Args:
            html: HTML content
            base_url: Base URL for resolving relative URLs

        Returns:
            List of image URLs
        """
        images = self.extract_images(html, base_url)
        return [img["src"] for img in images if img.get("src")]

    def _extract_img_data(self, img_tag, base_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Extract data from <img> tag.

        Args:
            img_tag: BeautifulSoup img tag
            base_url: Base URL for resolving relative URLs

        Returns:
            Dictionary with image data
        """
        # Get src (prefer srcset if available)
        src = img_tag.get("data-src") or img_tag.get("src")

        if not src:
            return None

        # Skip data URIs for URL list (but include in metadata)
        is_data_uri = src.startswith("data:")

        if not is_data_uri and base_url:
            src = urljoin(base_url, src)

        image_data = {
            "src": src,
            "alt": img_tag.get("alt", ""),
            "title": img_tag.get("title", ""),
            "width": img_tag.get("width"),
            "height": img_tag.get("height"),
            "class": img_tag.get("class", []),
            "id": img_tag.get("id"),
            "loading": img_tag.get("loading"),
            "is_data_uri": is_data_uri
        }

        # Extract srcset
        srcset = img_tag.get("srcset")
        if srcset:
            image_data["srcset"] = self._parse_srcset(srcset, base_url)

        return image_data

    def _parse_srcset(self, srcset: str, base_url: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Parse srcset attribute.

        Args:
            srcset: srcset attribute value
            base_url: Base URL for resolving relative URLs

        Returns:
            List of dictionaries with url and descriptor
        """
        sources = []

        for source in srcset.split(','):
            parts = source.strip().split()
            if not parts:
                continue

            url = parts[0]
            descriptor = parts[1] if len(parts) > 1 else "1x"

            if base_url and not url.startswith(('http://', 'https://', 'data:')):
                url = urljoin(base_url, url)

            sources.append({
                "url": url,
                "descriptor": descriptor
            })

        return sources

    def _extract_css_background(self, element, base_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Extract background image from CSS style.

        Args:
            element: BeautifulSoup element with style attribute
            base_url: Base URL for resolving relative URLs

        Returns:
            Dictionary with image data
        """
        style = element.get("style", "")
        match = re.search(r'background-image:\s*url\(["\']?([^"\']+)["\']?\)', style)

        if not match:
            return None

        url = match.group(1)

        if base_url and not url.startswith(('http://', 'https://', 'data:')):
            url = urljoin(base_url, url)

        return {
            "src": url,
            "source": "css-background",
            "element": element.name,
            "is_data_uri": url.startswith("data:")
        }

    def _extract_picture_data(self, picture_tag, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract data from <picture> element.

        Args:
            picture_tag: BeautifulSoup picture tag
            base_url: Base URL for resolving relative URLs

        Returns:
            List of dictionaries with image data
        """
        images = []

        # Extract sources
        for source in picture_tag.find_all("source"):
            srcset = source.get("srcset")
            if srcset:
                parsed_srcset = self._parse_srcset(srcset, base_url)
                images.append({
                    "sources": parsed_srcset,
                    "media": source.get("media"),
                    "type": source.get("type"),
                    "source": "picture-source"
                })

        # Extract fallback img
        img = picture_tag.find("img")
        if img:
            img_data = self._extract_img_data(img, base_url)
            if img_data:
                img_data["source"] = "picture-fallback"
                images.append(img_data)

        return images

    def extract_by_selector(self, html: str, selector: str, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract images matching a CSS selector.

        Args:
            html: HTML content
            selector: CSS selector
            base_url: Base URL for resolving relative URLs

        Returns:
            List of dictionaries with image data
        """
        soup = BeautifulSoup(html, "lxml")
        base_url = base_url or self.base_url

        images = []
        for element in soup.select(selector):
            if element.name == "img":
                image_data = self._extract_img_data(element, base_url)
                if image_data:
                    images.append(image_data)

        return images

    def extract_og_image(self, html: str, base_url: Optional[str] = None) -> Optional[str]:
        """
        Extract Open Graph image.

        Args:
            html: HTML content
            base_url: Base URL for resolving relative URLs

        Returns:
            OG image URL or None
        """
        soup = BeautifulSoup(html, "lxml")

        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            url = og_image["content"]

            if base_url and not url.startswith(('http://', 'https://')):
                url = urljoin(base_url, url)

            return url

        return None

    def extract_favicon(self, html: str, base_url: Optional[str] = None) -> Optional[str]:
        """
        Extract favicon URL.

        Args:
            html: HTML content
            base_url: Base URL for resolving relative URLs

        Returns:
            Favicon URL or None
        """
        soup = BeautifulSoup(html, "lxml")

        # Try various favicon selectors
        selectors = [
            'link[rel="icon"]',
            'link[rel="shortcut icon"]',
            'link[rel="apple-touch-icon"]'
        ]

        for selector in selectors:
            link = soup.select_one(selector)
            if link and link.get("href"):
                url = link["href"]

                if base_url and not url.startswith(('http://', 'https://', 'data:')):
                    url = urljoin(base_url, url)

                return url

        # Default favicon location
        if base_url:
            parsed = urlparse(base_url)
            return f"{parsed.scheme}://{parsed.netloc}/favicon.ico"

        return None

    def filter_by_size(self, images: List[Dict[str, Any]], min_width: Optional[int] = None, min_height: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Filter images by minimum dimensions.

        Args:
            images: List of image dictionaries
            min_width: Minimum width
            min_height: Minimum height

        Returns:
            Filtered list of images
        """
        filtered = []

        for img in images:
            width = img.get("width")
            height = img.get("height")

            # Skip if dimensions not available
            if not width or not height:
                filtered.append(img)
                continue

            try:
                width = int(width)
                height = int(height)

                if min_width and width < min_width:
                    continue
                if min_height and height < min_height:
                    continue

                filtered.append(img)

            except (ValueError, TypeError):
                # If can't parse dimensions, include image
                filtered.append(img)

        return filtered

    def extract_data_uri_info(self, data_uri: str) -> Optional[Dict[str, str]]:
        """
        Extract information from data URI.

        Args:
            data_uri: Data URI string

        Returns:
            Dictionary with MIME type and encoding info
        """
        if not data_uri.startswith("data:"):
            return None

        match = re.match(r'data:([^;]+);([^,]+),(.+)', data_uri)
        if match:
            return {
                "mime_type": match.group(1),
                "encoding": match.group(2),
                "data_length": len(match.group(3))
            }

        return None
