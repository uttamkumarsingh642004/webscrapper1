"""
Basic scraping examples.

Demonstrates simple scraping operations.
"""

from web_scraper.scrapers.static_scraper import StaticScraper
from web_scraper.exporters.json_exporter import JSONExporter


def example_1_simple_scraping():
    """Example 1: Simple URL scraping."""
    print("Example 1: Simple URL scraping")
    print("-" * 50)

    # Create scraper with minimal config
    config = {
        "scraping": {
            "rate_limit": 1.0
        },
        "error_handling": {
            "log_level": "INFO"
        }
    }

    scraper = StaticScraper(config)

    # Scrape a URL
    url = "http://quotes.toscrape.com/"
    result = scraper.scrape(url)

    print(f"Scraped {url}")
    print(f"Status: {result.get('status_code')}")
    print(f"Title: {result.get('title', 'N/A')}")
    print()


def example_2_with_selectors():
    """Example 2: Scraping with CSS selectors."""
    print("Example 2: Scraping with CSS selectors")
    print("-" * 50)

    config = {
        "scraping": {"rate_limit": 1.0},
        "error_handling": {"log_level": "INFO"}
    }

    scraper = StaticScraper(config)

    url = "http://quotes.toscrape.com/"

    # Define selectors
    selectors = {
        "quotes": ".quote .text",
        "authors": ".quote .author",
        "tags": ".quote .tags"
    }

    # Scrape with selectors
    result = scraper.scrape(
        url,
        selectors=selectors,
        extract_all=True
    )

    print(f"Scraped {url}")
    if "extracted_data" in result:
        data = result["extracted_data"]
        print(f"Found {len(data.get('quotes', []))} quotes")
        print(f"First quote: {data.get('quotes', ['N/A'])[0]}")
        print(f"First author: {data.get('authors', ['N/A'])[0]}")
    print()


def example_3_multiple_urls():
    """Example 3: Scraping multiple URLs."""
    print("Example 3: Scraping multiple URLs")
    print("-" * 50)

    config = {
        "scraping": {
            "rate_limit": 2.0,
            "max_workers": 3
        },
        "error_handling": {"log_level": "INFO"},
        "advanced": {"show_progress_bar": True}
    }

    scraper = StaticScraper(config)

    urls = [
        "http://quotes.toscrape.com/page/1/",
        "http://quotes.toscrape.com/page/2/",
        "http://quotes.toscrape.com/page/3/"
    ]

    results = scraper.scrape_multiple(urls)

    print(f"Scraped {len(results)} URLs")
    print(f"All requests successful: {all(r.get('status_code') == 200 for r in results)}")
    print()


def example_4_with_export():
    """Example 4: Scraping and exporting to JSON."""
    print("Example 4: Scraping and exporting to JSON")
    print("-" * 50)

    config = {
        "scraping": {"rate_limit": 1.0},
        "error_handling": {"log_level": "INFO"}
    }

    scraper = StaticScraper(config)

    url = "http://quotes.toscrape.com/"

    selectors = {
        "quote": ".quote .text",
        "author": ".quote .author"
    }

    result = scraper.scrape(url, selectors=selectors, extract_all=True)

    # Export to JSON
    output_file = "examples/quotes.json"
    exporter = JSONExporter(output_file, indent=2)
    exporter.export([result])

    print(f"Data exported to {output_file}")
    print()


def example_5_pagination():
    """Example 5: Scraping with pagination."""
    print("Example 5: Scraping with pagination")
    print("-" * 50)

    config = {
        "scraping": {
            "rate_limit": 1.0,
            "max_pages": 3
        },
        "error_handling": {"log_level": "INFO"}
    }

    scraper = StaticScraper(config)

    base_url = "http://quotes.toscrape.com"

    results = scraper.scrape_with_pagination(
        base_url=base_url,
        page_param="page",
        start_page=1,
        max_pages=3
    )

    print(f"Scraped {len(results)} pages")
    print()


if __name__ == "__main__":
    print("Web Scraper - Basic Examples")
    print("=" * 50)
    print()

    example_1_simple_scraping()
    example_2_with_selectors()
    example_3_multiple_urls()
    example_4_with_export()
    example_5_pagination()

    print("All examples completed!")
