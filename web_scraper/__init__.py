"""
Professional Web Scraping Framework

A modular, production-ready web scraping framework with support for
multiple scraping engines, advanced features, and comprehensive error handling.
"""

__version__ = "1.0.0"
__author__ = "Web Scraper Team"
__license__ = "MIT"

from web_scraper.scrapers.base_scraper import BaseScraper
from web_scraper.scrapers.static_scraper import StaticScraper

__all__ = [
    "BaseScraper",
    "StaticScraper",
]
