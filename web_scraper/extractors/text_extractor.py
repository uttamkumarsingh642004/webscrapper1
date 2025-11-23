"""
Text extraction utilities.

Provides methods to extract and clean text from HTML content.
"""

import re
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag, NavigableString
import unicodedata


class TextExtractor:
    """
    Extract and clean text content from HTML.

    Provides various text extraction methods including
    full text, specific elements, and cleaned text.
    """

    def __init__(self, clean_whitespace: bool = True, remove_html_tags: bool = True, normalize_unicode: bool = True):
        """
        Initialize text extractor.

        Args:
            clean_whitespace: Whether to clean excessive whitespace
            remove_html_tags: Whether to remove HTML tags
            normalize_unicode: Whether to normalize Unicode characters
        """
        self.clean_whitespace = clean_whitespace
        self.remove_html_tags = remove_html_tags
        self.normalize_unicode = normalize_unicode

    def extract_text(self, html: str, selector: Optional[str] = None) -> str:
        """
        Extract text from HTML.

        Args:
            html: HTML content
            selector: Optional CSS selector to extract specific element

        Returns:
            Extracted text
        """
        soup = BeautifulSoup(html, "lxml")

        if selector:
            element = soup.select_one(selector)
            if not element:
                return ""
            text = element.get_text()
        else:
            text = soup.get_text()

        return self._clean_text(text)

    def extract_all_text(self, html: str, selector: str) -> List[str]:
        """
        Extract text from all matching elements.

        Args:
            html: HTML content
            selector: CSS selector

        Returns:
            List of extracted text strings
        """
        soup = BeautifulSoup(html, "lxml")
        elements = soup.select(selector)

        return [self._clean_text(el.get_text()) for el in elements]

    def extract_paragraphs(self, html: str) -> List[str]:
        """
        Extract all paragraph text.

        Args:
            html: HTML content

        Returns:
            List of paragraph texts
        """
        return self.extract_all_text(html, "p")

    def extract_headings(self, html: str, level: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Extract headings with their levels.

        Args:
            html: HTML content
            level: Specific heading level to extract (1-6) or None for all

        Returns:
            List of dictionaries with 'level' and 'text' keys
        """
        soup = BeautifulSoup(html, "lxml")

        if level:
            headings = soup.find_all(f"h{level}")
            return [{"level": level, "text": self._clean_text(h.get_text())} for h in headings]
        else:
            headings = []
            for i in range(1, 7):
                elements = soup.find_all(f"h{i}")
                headings.extend([{"level": i, "text": self._clean_text(h.get_text())} for h in elements])

            return headings

    def extract_list_items(self, html: str, list_type: Optional[str] = None) -> List[str]:
        """
        Extract list items.

        Args:
            html: HTML content
            list_type: Type of list ('ul', 'ol', or None for both)

        Returns:
            List of list item texts
        """
        soup = BeautifulSoup(html, "lxml")

        if list_type:
            lists = soup.find_all(list_type)
        else:
            lists = soup.find_all(["ul", "ol"])

        items = []
        for lst in lists:
            list_items = lst.find_all("li", recursive=False)
            items.extend([self._clean_text(li.get_text()) for li in list_items])

        return items

    def extract_metadata(self, html: str) -> Dict[str, str]:
        """
        Extract metadata from HTML (title, meta tags).

        Args:
            html: HTML content

        Returns:
            Dictionary of metadata
        """
        soup = BeautifulSoup(html, "lxml")
        metadata = {}

        # Extract title
        if soup.title:
            metadata["title"] = self._clean_text(soup.title.get_text())

        # Extract meta tags
        meta_tags = soup.find_all("meta")
        for meta in meta_tags:
            name = meta.get("name") or meta.get("property")
            content = meta.get("content")

            if name and content:
                metadata[name] = content

        return metadata

    def extract_text_between(self, html: str, start_selector: str, end_selector: str) -> str:
        """
        Extract text between two elements.

        Args:
            html: HTML content
            start_selector: CSS selector for start element
            end_selector: CSS selector for end element

        Returns:
            Text between elements
        """
        soup = BeautifulSoup(html, "lxml")

        start_elem = soup.select_one(start_selector)
        end_elem = soup.select_one(end_selector)

        if not start_elem or not end_elem:
            return ""

        text_parts = []
        current = start_elem.next_sibling

        while current and current != end_elem:
            if isinstance(current, NavigableString):
                text_parts.append(str(current))
            elif isinstance(current, Tag):
                text_parts.append(current.get_text())

            current = current.next_sibling

        return self._clean_text(" ".join(text_parts))

    def extract_by_regex(self, text: str, pattern: str, group: int = 0) -> List[str]:
        """
        Extract text using regex pattern.

        Args:
            text: Text to search
            pattern: Regex pattern
            group: Capture group to extract (0 for full match)

        Returns:
            List of matches
        """
        matches = re.finditer(pattern, text)

        if group == 0:
            return [match.group(0) for match in matches]
        else:
            return [match.group(group) for match in matches if len(match.groups()) >= group]

    def extract_emails(self, text: str) -> List[str]:
        """
        Extract email addresses from text.

        Args:
            text: Text to search

        Returns:
            List of email addresses
        """
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return list(set(re.findall(pattern, text)))

    def extract_phone_numbers(self, text: str) -> List[str]:
        """
        Extract phone numbers from text.

        Args:
            text: Text to search

        Returns:
            List of phone numbers
        """
        # Pattern for various phone formats
        patterns = [
            r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
            r'\(\d{3}\)\s*\d{3}-\d{4}',
            r'\d{3}-\d{3}-\d{4}'
        ]

        numbers = []
        for pattern in patterns:
            numbers.extend(re.findall(pattern, text))

        return list(set(numbers))

    def extract_urls(self, text: str) -> List[str]:
        """
        Extract URLs from text.

        Args:
            text: Text to search

        Returns:
            List of URLs
        """
        pattern = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
        return list(set(re.findall(pattern, text)))

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Normalize Unicode
        if self.normalize_unicode:
            text = unicodedata.normalize("NFKD", text)

        # Clean whitespace
        if self.clean_whitespace:
            # Replace multiple spaces/newlines with single space
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()

        return text

    def remove_stopwords(self, text: str, stopwords: Optional[List[str]] = None) -> str:
        """
        Remove stopwords from text.

        Args:
            text: Text to process
            stopwords: List of stopwords (or None for default English stopwords)

        Returns:
            Text with stopwords removed
        """
        if stopwords is None:
            # Common English stopwords
            stopwords = {
                "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
                "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
                "to", "was", "will", "with"
            }

        words = text.split()
        filtered_words = [word for word in words if word.lower() not in stopwords]

        return " ".join(filtered_words)

    def get_word_count(self, text: str) -> int:
        """
        Get word count of text.

        Args:
            text: Text to count

        Returns:
            Number of words
        """
        return len(text.split())

    def get_character_count(self, text: str, include_spaces: bool = True) -> int:
        """
        Get character count of text.

        Args:
            text: Text to count
            include_spaces: Whether to include spaces

        Returns:
            Number of characters
        """
        if include_spaces:
            return len(text)
        else:
            return len(text.replace(" ", ""))
