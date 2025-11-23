"""
Main entry point for the web scraper.

Provides programmatic access to the scraping functionality.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path

from web_scraper.config.config_loader import ConfigLoader
from web_scraper.scrapers.scraper_factory import ScraperFactory
from web_scraper.exporters.json_exporter import JSONExporter
from web_scraper.exporters.csv_exporter import CSVExporter, ExcelExporter
from web_scraper.exporters.db_exporter import SQLiteExporter, MongoDBExporter


class WebScraper:
    """
    Main web scraper class.

    Provides a high-level interface for web scraping operations.
    """

    def __init__(self, config_file: Optional[str] = None, **config_overrides):
        """
        Initialize web scraper.

        Args:
            config_file: Path to configuration file
            **config_overrides: Configuration overrides
        """
        # Load configuration
        self.config_loader = ConfigLoader(config_file)
        self.config = self.config_loader.to_dict()

        # Apply overrides
        if config_overrides:
            self.config_loader.update(config_overrides)
            self.config = self.config_loader.to_dict()

        # Initialize factory
        self.factory = ScraperFactory(self.config)

    def scrape(
        self,
        url: str,
        scraper_type: str = "auto",
        output_file: Optional[str] = None,
        output_format: str = "json",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Scrape a single URL.

        Args:
            url: URL to scrape
            scraper_type: Type of scraper to use
            output_file: Output file path (optional)
            output_format: Output format if file provided
            **kwargs: Additional scraping arguments

        Returns:
            Scraped data dictionary
        """
        # Create scraper
        scraper = self.factory.create_scraper(url, scraper_type)

        # Scrape
        result = scraper.scrape(url, **kwargs)

        # Export if output file specified
        if output_file:
            self.export([result], output_file, output_format)

        return result

    def scrape_multiple(
        self,
        urls: List[str],
        scraper_type: str = "auto",
        output_file: Optional[str] = None,
        output_format: str = "json",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs.

        Args:
            urls: List of URLs to scrape
            scraper_type: Type of scraper to use
            output_file: Output file path (optional)
            output_format: Output format if file provided
            **kwargs: Additional scraping arguments

        Returns:
            List of scraped data dictionaries
        """
        if not urls:
            return []

        # Create scraper using first URL
        scraper = self.factory.create_scraper(urls[0], scraper_type)

        # Scrape all URLs
        results = scraper.scrape_multiple(urls, **kwargs)

        # Export if output file specified
        if output_file:
            self.export(results, output_file, output_format)

        return results

    def scrape_with_pagination(
        self,
        base_url: str,
        max_pages: int = 10,
        page_param: str = "page",
        scraper_type: str = "auto",
        output_file: Optional[str] = None,
        output_format: str = "json",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Scrape with pagination.

        Args:
            base_url: Base URL
            max_pages: Maximum pages to scrape
            page_param: Page parameter name
            scraper_type: Type of scraper to use
            output_file: Output file path (optional)
            output_format: Output format if file provided
            **kwargs: Additional scraping arguments

        Returns:
            List of scraped data dictionaries
        """
        # Create scraper
        scraper = self.factory.create_scraper(base_url, scraper_type)

        # Check if scraper has pagination method
        if hasattr(scraper, 'scrape_with_pagination'):
            results = scraper.scrape_with_pagination(
                base_url,
                page_param=page_param,
                max_pages=max_pages,
                **kwargs
            )
        else:
            # Fallback: manually create URLs
            results = []
            for page in range(1, max_pages + 1):
                separator = "&" if "?" in base_url else "?"
                url = f"{base_url}{separator}{page_param}={page}"

                result = scraper.scrape(url, **kwargs)
                if result and not result.get("error"):
                    results.append(result)
                else:
                    break

        # Export if output file specified
        if output_file:
            self.export(results, output_file, output_format)

        return results

    def export(
        self,
        data: List[Dict[str, Any]],
        output_file: str,
        format: str = "json"
    ) -> None:
        """
        Export scraped data.

        Args:
            data: Data to export
            output_file: Output file path
            format: Export format
        """
        if format == "json":
            exporter = JSONExporter(output_file)
            exporter.export(data)
        elif format == "jsonl":
            exporter = JSONExporter(output_file)
            exporter.export_jsonl(data)
        elif format == "csv":
            exporter = CSVExporter(output_file)
            exporter.export(data)
        elif format == "excel":
            exporter = ExcelExporter(output_file)
            exporter.export(data)
        elif format == "sqlite":
            exporter = SQLiteExporter(output_file)
            exporter.export(data)
        elif format == "mongodb":
            db_config = self.config.get("export", {}).get("database", {})
            exporter = MongoDBExporter(
                output_file,
                mongodb_uri=db_config.get("mongodb_uri", "mongodb://localhost:27017/"),
                database_name=db_config.get("mongodb_database", "web_scraper"),
                collection_name=db_config.get("mongodb_collection", "scraped_data")
            )
            exporter.export(data)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def analyze_url(self, url: str) -> Dict[str, Any]:
        """
        Analyze URL and get scraper recommendation.

        Args:
            url: URL to analyze

        Returns:
            Analysis results
        """
        return self.factory.get_recommended_scraper_info(url)


def quick_scrape(
    url: str,
    output_file: Optional[str] = None,
    selectors: Optional[Dict[str, str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Quick scraping function for simple use cases.

    Args:
        url: URL to scrape
        output_file: Output file path
        selectors: CSS selectors dictionary
        **kwargs: Additional arguments

    Returns:
        Scraped data

    Example:
        >>> data = quick_scrape(
        ...     "https://example.com",
        ...     selectors={"title": "h1", "price": ".price"}
        ... )
    """
    scraper = WebScraper()

    scrape_kwargs = kwargs.copy()
    if selectors:
        scrape_kwargs["selectors"] = selectors

    return scraper.scrape(url, output_file=output_file, **scrape_kwargs)


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python main.py <url> [output_file]")
        sys.exit(1)

    url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "output.json"

    print(f"Scraping {url}...")

    scraper = WebScraper()
    result = scraper.scrape(url, output_file=output_file)

    print(f"Done! Data saved to {output_file}")
