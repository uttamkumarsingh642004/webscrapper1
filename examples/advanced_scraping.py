"""
Advanced scraping examples.

Demonstrates advanced features like dynamic scraping, API scraping, and exporters.
"""

from web_scraper.scrapers.api_scraper import APIScraper
from web_scraper.scrapers.scraper_factory import ScraperFactory
from web_scraper.exporters.csv_exporter import CSVExporter, ExcelExporter
from web_scraper.exporters.db_exporter import SQLiteExporter
from web_scraper.extractors.link_extractor import LinkExtractor
from web_scraper.extractors.image_extractor import ImageExtractor
from main import WebScraper


def example_1_api_scraping():
    """Example 1: Scraping REST API."""
    print("Example 1: API Scraping")
    print("-" * 50)

    config = {
        "scraping": {"rate_limit": 2.0},
        "error_handling": {"log_level": "INFO"}
    }

    scraper = APIScraper(config)

    # Example: JSONPlaceholder API
    url = "https://jsonplaceholder.typicode.com/posts/1"

    result = scraper.scrape(url, response_format="json")

    print(f"API Response: {result.get('success', False)}")
    if result.get("data"):
        data = result["data"]
        print(f"Title: {data.get('title', 'N/A')}")
        print(f"User ID: {data.get('userId', 'N/A')}")
    print()


def example_2_scraper_factory():
    """Example 2: Using scraper factory for auto-detection."""
    print("Example 2: Scraper Factory Auto-Detection")
    print("-" * 50)

    config = {
        "scraping": {"rate_limit": 1.0},
        "error_handling": {"log_level": "INFO"}
    }

    factory = ScraperFactory(config)

    # Test URLs
    urls = [
        "http://quotes.toscrape.com/",  # Static HTML
        "https://jsonplaceholder.typicode.com/posts",  # API
    ]

    for url in urls:
        info = factory.get_recommended_scraper_info(url)
        print(f"URL: {url}")
        print(f"Recommended: {info['recommended_scraper']}")
        print(f"Reasons: {', '.join(info['reasons'])}")
        print()


def example_3_data_extraction():
    """Example 3: Advanced data extraction."""
    print("Example 3: Advanced Data Extraction")
    print("-" * 50)

    from web_scraper.scrapers.static_scraper import StaticScraper

    config = {
        "scraping": {"rate_limit": 1.0},
        "error_handling": {"log_level": "INFO"}
    }

    scraper = StaticScraper(config)
    url = "http://quotes.toscrape.com/"

    result = scraper.scrape(url)

    if result.get("html"):
        html = result["html"]

        # Extract links
        link_extractor = LinkExtractor(base_url=url)
        links = link_extractor.extract_links(html)
        internal_links = link_extractor.filter_internal_links(html, url)

        print(f"Total links: {len(links)}")
        print(f"Internal links: {len(internal_links)}")

        # Extract images
        image_extractor = ImageExtractor(base_url=url)
        images = image_extractor.extract_images(html, url)

        print(f"Total images: {len(images)}")
        if images:
            print(f"First image: {images[0].get('src', 'N/A')}")

    print()


def example_4_export_formats():
    """Example 4: Exporting to different formats."""
    print("Example 4: Multiple Export Formats")
    print("-" * 50)

    # Sample data
    data = [
        {"name": "Product 1", "price": 29.99, "stock": 100},
        {"name": "Product 2", "price": 49.99, "stock": 50},
        {"name": "Product 3", "price": 19.99, "stock": 200},
    ]

    # Export to CSV
    csv_exporter = CSVExporter("examples/products.csv")
    csv_exporter.export(data)
    print("Exported to CSV: examples/products.csv")

    # Export to Excel
    excel_exporter = ExcelExporter("examples/products.xlsx", sheet_name="Products")
    excel_exporter.export(data)
    print("Exported to Excel: examples/products.xlsx")

    # Export to SQLite
    sqlite_exporter = SQLiteExporter("examples/products.db", table_name="products")
    sqlite_exporter.export(data)
    print("Exported to SQLite: examples/products.db")

    print()


def example_5_web_scraper_class():
    """Example 5: Using the main WebScraper class."""
    print("Example 5: WebScraper Class")
    print("-" * 50)

    # Create scraper with custom config
    scraper = WebScraper(
        scraping={"rate_limit": 2.0, "max_workers": 3},
        error_handling={"log_level": "INFO"}
    )

    # Analyze URL
    url = "http://quotes.toscrape.com/"
    analysis = scraper.analyze_url(url)

    print(f"Analysis for {url}:")
    print(f"Recommended scraper: {analysis['recommended_scraper']}")
    print(f"Reasons: {', '.join(analysis['reasons'])}")

    # Scrape with selectors
    result = scraper.scrape(
        url=url,
        selectors={"quote": ".quote .text"},
        extract_all=True
    )

    if result.get("extracted_data"):
        quotes = result["extracted_data"].get("quote", [])
        print(f"\nFound {len(quotes)} quotes")
        if quotes:
            print(f"First quote: {quotes[0]}")

    print()


def example_6_pagination_scraping():
    """Example 6: Pagination scraping."""
    print("Example 6: Pagination Scraping")
    print("-" * 50)

    scraper = WebScraper(
        scraping={"rate_limit": 1.0, "max_pages": 3},
        error_handling={"log_level": "INFO"}
    )

    results = scraper.scrape_with_pagination(
        base_url="http://quotes.toscrape.com",
        max_pages=3,
        page_param="page"
    )

    print(f"Scraped {len(results)} pages")
    print(f"All successful: {all(r.get('status_code') == 200 for r in results)}")
    print()


if __name__ == "__main__":
    print("Web Scraper - Advanced Examples")
    print("=" * 50)
    print()

    example_1_api_scraping()
    example_2_scraper_factory()
    example_3_data_extraction()
    example_4_export_formats()
    example_5_web_scraper_class()
    example_6_pagination_scraping()

    print("All examples completed!")
