# Professional Web Scraping Framework

A production-ready, modular web scraping framework with support for multiple scraping engines, advanced features, and comprehensive error handling.

## Features

### Multiple Scraping Engines
- **BeautifulSoup4** - Fast, lightweight scraping for static HTML
- **Selenium** - JavaScript-heavy sites with headless Chrome/Firefox
- **Playwright** - Modern alternative for dynamic content
- **Requests + lxml** - High-performance static scraping
- **API Scraper** - REST API endpoint scraping

### Key Capabilities
- ✅ **Automatic Scraper Detection** - Intelligently selects the best scraper for each website
- ✅ **CSS Selector & XPath Support** - Flexible data extraction
- ✅ **Regex Pattern Matching** - Advanced text extraction
- ✅ **Pagination Handling** - Infinite scroll, numbered pages, "load more" buttons
- ✅ **AJAX/Dynamic Content** - Automatic detection and handling
- ✅ **Form Submission & Authentication** - Login and form handling
- ✅ **Proxy Rotation** - Automatic proxy management and rotation
- ✅ **User-Agent Rotation** - Realistic user-agent strings
- ✅ **Rate Limiting** - Configurable request rate and politeness delays
- ✅ **Concurrent Scraping** - Thread pool-based parallel scraping
- ✅ **Retry Logic** - Exponential backoff for failed requests
- ✅ **Robots.txt Compliance** - Automatic robots.txt checking

### Data Handling
- 📊 **Multiple Export Formats** - JSON, CSV, Excel, SQLite, MongoDB
- 🧹 **Data Cleaning** - Automatic normalization and cleaning
- 🔍 **Duplicate Detection** - Intelligent duplicate removal
- 💾 **Incremental Scraping** - Resume from where you stopped
- ✔️ **Schema Validation** - Validate output data structure

### Error Management
- 🚨 **Comprehensive Error Handling** - Network issues, timeouts, 404s
- 📝 **Advanced Logging** - Multiple verbosity levels
- 🔄 **Retry Queue** - Failed requests with retry mechanism
- 📸 **Screenshot Capture** - Debug screenshots on errors
- 🤖 **Captcha Detection** - Notifications when captchas detected

## Installation

### Requirements
- Python 3.8+
- pip

### Quick Install

```bash
# Clone repository
git clone <repository-url>
cd webscrapper1

# Install dependencies
pip install -r requirements.txt

# Install browsers for Playwright (optional)
playwright install
```

### Install Specific Components

```bash
# Minimal installation (static scraping only)
pip install requests beautifulsoup4 lxml pyyaml pandas

# With Selenium
pip install selenium webdriver-manager

# With Playwright
pip install playwright
playwright install

# With MongoDB
pip install pymongo
```

## Quick Start

### Command Line Interface

```bash
# Simple scraping
python cli.py --url "https://example.com" --output data.json

# With CSS selectors
python cli.py --url "https://example.com" \
  --fields "title:h1,price:.price-class" \
  --output products.csv

# Multiple pages
python cli.py --url "https://example.com" \
  --pages 10 \
  --output data.json

# With proxy and rate limiting
python cli.py --url "https://example.com" \
  --proxy-file proxies.txt \
  --rate-limit 2 \
  --output data.json
```

### Python API

```python
from main import WebScraper

# Create scraper instance
scraper = WebScraper()

# Simple scraping
result = scraper.scrape(
    url="https://example.com",
    output_file="data.json"
)

# With selectors
result = scraper.scrape(
    url="https://example.com",
    selectors={
        "title": "h1.product-title",
        "price": ".price",
        "description": ".desc"
    },
    extract_all=True
)

# Multiple URLs
results = scraper.scrape_multiple(
    urls=["https://example.com/page1", "https://example.com/page2"],
    output_file="results.json"
)

# With pagination
results = scraper.scrape_with_pagination(
    base_url="https://example.com/products",
    max_pages=10,
    page_param="page",
    output_file="products.json"
)
```

### Quick Scrape Function

```python
from main import quick_scrape

# One-liner scraping
data = quick_scrape(
    url="https://example.com",
    selectors={"title": "h1", "price": ".price"}
)
```

## Configuration

### Using Configuration Files

Create a YAML or JSON configuration file:

```yaml
# config.yaml
scraping:
  scraper_type: "auto"
  rate_limit: 2.0
  max_workers: 5
  headless: true

extraction:
  css_selectors:
    title: "h1.title"
    price: ".price"
  remove_duplicates: true

export:
  format: "json"
  output_file: "scraped_data.json"

error_handling:
  log_level: "INFO"
  continue_on_error: true
```

Use the configuration:

```bash
python cli.py --config config.yaml
```

Or in Python:

```python
scraper = WebScraper(config_file="config.yaml")
```

### Environment Variables

Configuration supports environment variable substitution:

```yaml
request:
  auth:
    token: "${API_TOKEN}"

export:
  database:
    mongodb_uri: "${MONGO_URI}"
```

## Advanced Usage

### Custom Scraper Selection

```python
from web_scraper.scrapers.static_scraper import StaticScraper
from web_scraper.scrapers.selenium_scraper import SeleniumScraper

# Use specific scraper
config = {"scraping": {"rate_limit": 2.0}}
scraper = StaticScraper(config)

# Or use Selenium for JavaScript-heavy sites
scraper = SeleniumScraper(config)
result = scraper.scrape("https://spa-website.com")
```

### Data Extraction

```python
# Text extraction
from web_scraper.extractors.text_extractor import TextExtractor

extractor = TextExtractor()
text = extractor.extract_text(html, selector="article")
emails = extractor.extract_emails(text)
phone_numbers = extractor.extract_phone_numbers(text)

# Image extraction
from web_scraper.extractors.image_extractor import ImageExtractor

img_extractor = ImageExtractor(base_url="https://example.com")
images = img_extractor.extract_images(html)
og_image = img_extractor.extract_og_image(html)

# Link extraction
from web_scraper.extractors.link_extractor import LinkExtractor

link_extractor = LinkExtractor(base_url="https://example.com")
links = link_extractor.extract_links(html)
internal_links = link_extractor.filter_internal_links(html)
nav_links = link_extractor.extract_navigation_links(html)

# Table extraction
from web_scraper.extractors.table_extractor import TableExtractor

table_extractor = TableExtractor()
tables = table_extractor.extract_tables(html)
df = table_extractor.extract_table_to_dataframe(html, index=0)
```

### Data Export

```python
from web_scraper.exporters.json_exporter import JSONExporter
from web_scraper.exporters.csv_exporter import CSVExporter, ExcelExporter
from web_scraper.exporters.db_exporter import SQLiteExporter, MongoDBExporter

# JSON
exporter = JSONExporter("output.json", indent=2)
exporter.export(data)

# CSV
exporter = CSVExporter("output.csv", delimiter=",")
exporter.export(data)

# Excel
exporter = ExcelExporter("output.xlsx", sheet_name="Results")
exporter.export(data)

# SQLite
exporter = SQLiteExporter("output.db", table_name="scraped_data")
exporter.export(data)

# MongoDB
exporter = MongoDBExporter(
    output_file="",
    mongodb_uri="mongodb://localhost:27017/",
    database_name="scraper_db",
    collection_name="data"
)
exporter.export(data)
```

### Infinite Scroll

```python
from web_scraper.scrapers.selenium_scraper import SeleniumScraper

scraper = SeleniumScraper(config)
result = scraper.scrape_with_infinite_scroll(
    url="https://infinite-scroll-site.com",
    max_scrolls=10,
    pause_time=2.0
)
```

### Proxy Rotation

```python
# Via configuration
config = {
    "request": {
        "use_proxy": True,
        "proxy_file": "proxies.txt",
        "rotate_proxy": True
    }
}

scraper = WebScraper(**config)
```

Or manually:

```python
from web_scraper.utils.proxy_manager import ProxyManager

proxy_manager = ProxyManager(
    proxy_file="proxies.txt",
    rotation_strategy="round_robin"  # or "random", "weighted"
)

proxy = proxy_manager.get_proxy()
```

### Rate Limiting

```python
from web_scraper.utils.rate_limiter import RateLimiter, AdaptiveRateLimiter

# Fixed rate limiter
limiter = RateLimiter(requests_per_second=2.0, delay_between_requests=0.5)
limiter.acquire()  # Block until token available

# Adaptive rate limiter (adjusts based on responses)
adaptive_limiter = AdaptiveRateLimiter(
    initial_rate=5.0,
    min_rate=0.5,
    max_rate=10.0
)

# Report success/failure to adjust rate
adaptive_limiter.report_success()
adaptive_limiter.report_failure()
```

## Project Structure

```
web_scraper/
├── scrapers/
│   ├── base_scraper.py          # Abstract base class
│   ├── static_scraper.py        # BeautifulSoup scraper
│   ├── selenium_scraper.py      # Selenium scraper
│   ├── playwright_scraper.py    # Playwright scraper
│   ├── api_scraper.py           # API scraper
│   └── scraper_factory.py       # Auto-detection factory
├── extractors/
│   ├── text_extractor.py        # Text extraction
│   ├── image_extractor.py       # Image extraction
│   ├── link_extractor.py        # Link extraction
│   └── table_extractor.py       # Table extraction
├── utils/
│   ├── rate_limiter.py          # Rate limiting
│   ├── proxy_manager.py         # Proxy management
│   ├── user_agent_rotator.py   # User-agent rotation
│   ├── robots_checker.py        # Robots.txt checker
│   └── logger.py                # Logging utility
├── exporters/
│   ├── base_exporter.py         # Base exporter
│   ├── json_exporter.py         # JSON export
│   ├── csv_exporter.py          # CSV/Excel export
│   └── db_exporter.py           # Database export
├── config/
│   ├── default_config.yaml      # Default configuration
│   └── config_loader.py         # Configuration loader
└── tests/                       # Unit tests

cli.py                           # Command-line interface
main.py                          # Main entry point
requirements.txt                 # Dependencies
README.md                        # Documentation
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=web_scraper --cov-report=html

# Run specific test file
pytest tests/test_static_scraper.py
```

## Examples

See the `examples/` directory for complete examples:

- `basic_scraping.py` - Basic scraping examples
- `example_config.yaml` - Example configuration file

## Performance Tips

1. **Use Static Scraper When Possible** - Much faster than dynamic scrapers
2. **Enable Concurrency** - Set `max_workers` > 1 for multiple URLs
3. **Optimize Selectors** - Use specific CSS selectors to reduce parsing time
4. **Cache Results** - Enable caching for repeated requests
5. **Use Appropriate Rate Limits** - Balance speed with server respect

## Troubleshooting

### Common Issues

**"Module not found" errors**
```bash
pip install -r requirements.txt
```

**Selenium browser not found**
```bash
# webdriver-manager handles this automatically, but you can also:
# For Chrome:
# Download chromedriver from https://chromedriver.chromium.org/

# For Firefox:
# Download geckodriver from https://github.com/mozilla/geckodriver/releases
```

**Playwright installation issues**
```bash
playwright install
```

**MongoDB connection errors**
```bash
# Make sure MongoDB is running:
sudo systemctl start mongod

# Or use Docker:
docker run -d -p 27017:27017 mongo
```

## Best Practices

1. **Respect robots.txt** - Keep `respect_robots_txt: true`
2. **Use Rate Limiting** - Don't overload servers
3. **Rotate User Agents** - Appear as different browsers
4. **Handle Errors Gracefully** - Enable `continue_on_error`
5. **Log Everything** - Set appropriate `log_level`
6. **Test on Small Samples** - Before scraping large datasets
7. **Monitor Resources** - Watch memory and bandwidth usage

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Disclaimer

This tool is for educational and research purposes. Always:
- Respect website Terms of Service
- Follow robots.txt directives
- Use appropriate rate limiting
- Don't scrape private/sensitive data
- Check legal requirements in your jurisdiction

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check documentation in `/docs`
- Review examples in `/examples`

## Changelog

### Version 1.0.0 (Initial Release)
- Multiple scraping engines (BeautifulSoup, Selenium, Playwright)
- Automatic scraper detection
- Comprehensive data extraction utilities
- Multiple export formats
- Advanced error handling and retry logic
- Rate limiting and proxy support
- Full CLI interface
- Extensive documentation

---

**Built with ❤️ for the web scraping community**
