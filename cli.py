"""
Command-line interface for the web scraper.

Provides a user-friendly CLI for scraping websites.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any

from web_scraper.config.config_loader import ConfigLoader
from web_scraper.scrapers.scraper_factory import create_scraper
from web_scraper.exporters.json_exporter import JSONExporter
from web_scraper.exporters.csv_exporter import CSVExporter, ExcelExporter
from web_scraper.exporters.db_exporter import SQLiteExporter, MongoDBExporter


def parse_fields(fields_str: str) -> Dict[str, str]:
    """
    Parse field mappings from string.

    Format: "name:selector,price:.price-class"

    Args:
        fields_str: Field mappings string

    Returns:
        Dictionary of field mappings
    """
    fields = {}

    for field_mapping in fields_str.split(','):
        if ':' in field_mapping:
            name, selector = field_mapping.split(':', 1)
            fields[name.strip()] = selector.strip()

    return fields


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Professional Web Scraping Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple scraping
  python cli.py --url "https://example.com" --output data.json

  # With CSS selectors
  python cli.py --url "https://example.com" \\
    --selector "div.product" \\
    --fields "title:.title,price:.price" \\
    --output products.csv

  # Using configuration file
  python cli.py --config scrape_config.yaml

  # With proxy and rate limiting
  python cli.py --url "https://example.com" \\
    --proxy-file proxies.txt \\
    --rate-limit 2 \\
    --output data.json

  # Multiple pages
  python cli.py --url "https://example.com" \\
    --pages 10 \\
    --output data.json
        """
    )

    # Input arguments
    input_group = parser.add_argument_group('Input Options')
    input_group.add_argument(
        '--url',
        type=str,
        help='URL to scrape'
    )
    input_group.add_argument(
        '--urls-file',
        type=str,
        help='File containing URLs to scrape (one per line)'
    )
    input_group.add_argument(
        '--config',
        type=str,
        help='Configuration file (YAML or JSON)'
    )

    # Scraper options
    scraper_group = parser.add_argument_group('Scraper Options')
    scraper_group.add_argument(
        '--scraper-type',
        choices=['auto', 'static', 'selenium', 'playwright', 'api'],
        default='auto',
        help='Scraper type to use (default: auto)'
    )
    scraper_group.add_argument(
        '--browser',
        choices=['chrome', 'firefox', 'chromium', 'webkit'],
        help='Browser to use for dynamic scrapers'
    )
    scraper_group.add_argument(
        '--headless',
        action='store_true',
        default=True,
        help='Run browser in headless mode (default: True)'
    )
    scraper_group.add_argument(
        '--no-headless',
        action='store_false',
        dest='headless',
        help='Run browser with UI'
    )

    # Extraction options
    extraction_group = parser.add_argument_group('Extraction Options')
    extraction_group.add_argument(
        '--selector',
        type=str,
        help='CSS selector for main content'
    )
    extraction_group.add_argument(
        '--fields',
        type=str,
        help='Field mappings (format: "name:selector,price:.price")'
    )
    extraction_group.add_argument(
        '--xpath',
        type=str,
        help='XPath expression'
    )
    extraction_group.add_argument(
        '--extract-all',
        action='store_true',
        help='Extract all matching elements (default: first match)'
    )

    # Pagination options
    pagination_group = parser.add_argument_group('Pagination Options')
    pagination_group.add_argument(
        '--pages',
        type=int,
        help='Number of pages to scrape'
    )
    pagination_group.add_argument(
        '--page-param',
        type=str,
        default='page',
        help='URL parameter for page number (default: page)'
    )
    pagination_group.add_argument(
        '--infinite-scroll',
        action='store_true',
        help='Handle infinite scroll'
    )

    # Rate limiting and proxy options
    network_group = parser.add_argument_group('Network Options')
    network_group.add_argument(
        '--rate-limit',
        type=float,
        help='Requests per second (default: 1.0)'
    )
    network_group.add_argument(
        '--delay',
        type=float,
        help='Delay between requests in seconds'
    )
    network_group.add_argument(
        '--proxy',
        type=str,
        help='Single proxy URL'
    )
    network_group.add_argument(
        '--proxy-file',
        type=str,
        help='File containing proxy URLs (one per line)'
    )
    network_group.add_argument(
        '--timeout',
        type=int,
        help='Request timeout in seconds (default: 30)'
    )
    network_group.add_argument(
        '--max-retries',
        type=int,
        help='Maximum retry attempts (default: 3)'
    )

    # Concurrency options
    concurrency_group = parser.add_argument_group('Concurrency Options')
    concurrency_group.add_argument(
        '--max-workers',
        type=int,
        help='Maximum concurrent workers (default: 5)'
    )

    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument(
        '--output',
        '-o',
        type=str,
        required=True,
        help='Output file path'
    )
    output_group.add_argument(
        '--format',
        choices=['json', 'jsonl', 'csv', 'excel', 'sqlite', 'mongodb'],
        help='Output format (auto-detected from file extension if not specified)'
    )
    output_group.add_argument(
        '--remove-duplicates',
        action='store_true',
        help='Remove duplicate entries'
    )

    # Advanced options
    advanced_group = parser.add_argument_group('Advanced Options')
    advanced_group.add_argument(
        '--respect-robots-txt',
        action='store_true',
        default=True,
        help='Respect robots.txt (default: True)'
    )
    advanced_group.add_argument(
        '--no-respect-robots-txt',
        action='store_false',
        dest='respect_robots_txt',
        help='Ignore robots.txt'
    )
    advanced_group.add_argument(
        '--screenshots',
        action='store_true',
        help='Take screenshots (for dynamic scrapers)'
    )
    advanced_group.add_argument(
        '--screenshot-dir',
        type=str,
        default='screenshots',
        help='Directory for screenshots'
    )
    advanced_group.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    advanced_group.add_argument(
        '--log-file',
        type=str,
        help='Log file path'
    )
    advanced_group.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress bar'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.url and not args.urls_file and not args.config:
        parser.error("Either --url, --urls-file, or --config is required")

    try:
        # Load configuration
        config_loader = ConfigLoader(args.config) if args.config else ConfigLoader()
        config = config_loader.to_dict()

        # Override config with CLI arguments
        if args.scraper_type:
            config['scraping']['scraper_type'] = args.scraper_type
        if args.browser:
            config['scraping']['browser'] = args.browser
        if args.headless is not None:
            config['scraping']['headless'] = args.headless
        if args.rate_limit:
            config['scraping']['rate_limit'] = args.rate_limit
        if args.delay:
            config['scraping']['delay_between_requests'] = args.delay
        if args.timeout:
            config['scraping']['timeout'] = args.timeout
        if args.max_retries:
            config['scraping']['max_retries'] = args.max_retries
        if args.max_workers:
            config['scraping']['max_workers'] = args.max_workers
        if args.pages:
            config['scraping']['max_pages'] = args.pages
        if args.log_level:
            config['error_handling']['log_level'] = args.log_level
        if args.log_file:
            config['error_handling']['log_file'] = args.log_file
        if args.respect_robots_txt is not None:
            config['advanced']['respect_robots_txt'] = args.respect_robots_txt
        if args.screenshots:
            config['advanced']['take_screenshots'] = True
        if args.screenshot_dir:
            config['advanced']['screenshot_dir'] = args.screenshot_dir
        if args.no_progress:
            config['advanced']['show_progress_bar'] = False

        # Set proxy configuration
        if args.proxy:
            config['request']['use_proxy'] = True
            # Create temp proxy file
            import tempfile
            proxy_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            proxy_file.write(args.proxy)
            proxy_file.close()
            config['request']['proxy_file'] = proxy_file.name
        elif args.proxy_file:
            config['request']['use_proxy'] = True
            config['request']['proxy_file'] = args.proxy_file

        # Set extraction configuration
        if args.fields:
            field_mappings = parse_fields(args.fields)
            config['extraction']['css_selectors'] = field_mappings

        # Create scraper
        url = args.url
        urls = []

        if args.urls_file:
            with open(args.urls_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
        elif url:
            urls = [url]

        if not urls:
            print("Error: No URLs to scrape", file=sys.stderr)
            return 1

        # Create scraper instance
        scraper = create_scraper(
            url=urls[0],
            scraper_type=args.scraper_type,
            config=config
        )

        print(f"Starting scraping with {config['scraping']['scraper_type']} scraper...")

        # Prepare scraping kwargs
        scrape_kwargs = {}
        if args.selector:
            scrape_kwargs['selectors'] = {args.selector: args.selector}
        if args.fields:
            scrape_kwargs['selectors'] = parse_fields(args.fields)
        if args.extract_all:
            scrape_kwargs['extract_all'] = True

        # Scrape URLs
        if len(urls) == 1 and args.pages:
            # Pagination
            results = scraper.scrape_with_pagination(
                urls[0],
                page_param=args.page_param,
                max_pages=args.pages,
                **scrape_kwargs
            )
        else:
            # Multiple URLs
            results = scraper.scrape_multiple(urls, **scrape_kwargs)

        # Determine export format
        export_format = args.format
        if not export_format:
            # Auto-detect from file extension
            ext = Path(args.output).suffix.lower()
            format_map = {
                '.json': 'json',
                '.jsonl': 'jsonl',
                '.csv': 'csv',
                '.xlsx': 'excel',
                '.xls': 'excel',
                '.db': 'sqlite',
                '.sqlite': 'sqlite'
            }
            export_format = format_map.get(ext, 'json')

        # Export results
        print(f"Exporting {len(results)} items to {args.output}...")

        if export_format == 'json':
            exporter = JSONExporter(args.output)
            exporter.export(results)
        elif export_format == 'jsonl':
            exporter = JSONExporter(args.output)
            exporter.export_jsonl(results)
        elif export_format == 'csv':
            exporter = CSVExporter(args.output)
            exporter.export(results)
        elif export_format == 'excel':
            exporter = ExcelExporter(args.output)
            exporter.export(results)
        elif export_format == 'sqlite':
            exporter = SQLiteExporter(args.output)
            exporter.export(results)
        elif export_format == 'mongodb':
            exporter = MongoDBExporter(
                args.output,
                mongodb_uri=config.get('export', {}).get('database', {}).get('mongodb_uri', 'mongodb://localhost:27017/')
            )
            exporter.export(results)

        # Print statistics
        stats = scraper.get_stats()
        print("\nScraping Statistics:")
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Successful: {stats['successful_requests']}")
        print(f"  Failed: {stats['failed_requests']}")
        print(f"  Items scraped: {stats['total_items_scraped']}")

        if stats.get('duration'):
            print(f"  Duration: {stats['duration']:.2f} seconds")
            print(f"  Rate: {stats.get('requests_per_second', 0):.2f} req/s")

        print(f"\nData exported to: {args.output}")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
