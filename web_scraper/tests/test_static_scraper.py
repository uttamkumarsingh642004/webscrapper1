"""
Unit tests for static scraper.
"""

import pytest
from web_scraper.scrapers.static_scraper import StaticScraper


class TestStaticScraper:
    """Test cases for StaticScraper."""

    @pytest.fixture
    def scraper(self):
        """Create scraper instance for testing."""
        config = {
            "scraping": {
                "rate_limit": 1.0,
                "timeout": 10
            },
            "error_handling": {
                "log_level": "ERROR",  # Reduce noise in tests
                "log_to_console": False
            },
            "advanced": {
                "respect_robots_txt": False,  # Skip for tests
                "show_progress_bar": False
            }
        }
        return StaticScraper(config)

    def test_scraper_initialization(self, scraper):
        """Test scraper initializes correctly."""
        assert scraper is not None
        assert scraper.timeout == 10
        assert scraper.parser == "lxml"

    def test_simple_scraping(self, scraper):
        """Test simple URL scraping."""
        # Using a test site
        url = "http://quotes.toscrape.com/"

        result = scraper.scrape(url)

        assert result is not None
        assert "url" in result
        assert "status_code" in result
        assert result["status_code"] == 200
        assert "html" in result

    def test_scraping_with_css_selectors(self, scraper):
        """Test scraping with CSS selectors."""
        url = "http://quotes.toscrape.com/"

        selectors = {
            "quotes": ".quote .text"
        }

        result = scraper.scrape(url, selectors=selectors, extract_all=True)

        assert "extracted_data" in result
        assert "quotes" in result["extracted_data"]
        assert len(result["extracted_data"]["quotes"]) > 0

    def test_extract_element_data(self, scraper):
        """Test extracting element data."""
        from bs4 import BeautifulSoup

        html = '<div class="test">Hello World</div>'
        soup = BeautifulSoup(html, "lxml")
        element = soup.select_one(".test")

        text = scraper._extract_element_data(element)

        assert text == "Hello World"

    def test_extract_with_regex(self, scraper):
        """Test regex extraction."""
        text = "Email: test@example.com, Phone: 123-456-7890"
        patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        }

        result = scraper._extract_with_regex(text, patterns, extract_all=False)

        assert "email" in result
        assert result["email"] == "test@example.com"

    def test_scrape_invalid_url(self, scraper):
        """Test scraping invalid URL."""
        url = "http://this-does-not-exist-xyz123456.com/"

        result = scraper.scrape(url)

        assert "error" in result
        assert result["success"] == False

    def test_stats_tracking(self, scraper):
        """Test statistics tracking."""
        url = "http://quotes.toscrape.com/"

        # Initial stats
        stats = scraper.get_stats()
        assert stats["total_requests"] == 0

        # After scraping
        scraper.scrape(url)
        stats = scraper.get_stats()

        assert stats["total_requests"] > 0
        assert stats["total_items_scraped"] >= 0


class TestRateLimiter:
    """Test rate limiting functionality."""

    def test_rate_limiter_import(self):
        """Test rate limiter can be imported."""
        from web_scraper.utils.rate_limiter import RateLimiter

        limiter = RateLimiter(requests_per_second=2.0)
        assert limiter.rate == 2.0

    def test_rate_limiter_stats(self):
        """Test rate limiter statistics."""
        from web_scraper.utils.rate_limiter import RateLimiter

        limiter = RateLimiter(requests_per_second=10.0)

        # Acquire a token
        limiter.acquire()

        stats = limiter.get_stats()
        assert stats["total_requests"] == 1


class TestProxyManager:
    """Test proxy management functionality."""

    def test_proxy_manager_with_list(self):
        """Test proxy manager with proxy list."""
        from web_scraper.utils.proxy_manager import ProxyManager

        proxies = [
            "http://proxy1.example.com:8080",
            "http://proxy2.example.com:8080"
        ]

        manager = ProxyManager(proxies=proxies)

        proxy = manager.get_proxy()

        assert proxy is not None
        assert "http" in proxy
        assert "https" in proxy


class TestConfigLoader:
    """Test configuration loading."""

    def test_config_loader_default(self):
        """Test default configuration loading."""
        from web_scraper.config.config_loader import ConfigLoader

        loader = ConfigLoader()
        config = loader.to_dict()

        assert "scraping" in config
        assert "export" in config
        assert "error_handling" in config

    def test_config_get(self):
        """Test getting configuration values."""
        from web_scraper.config.config_loader import ConfigLoader

        loader = ConfigLoader()

        # Test dot notation
        value = loader.get("scraping.timeout")
        assert value is not None

    def test_config_set(self):
        """Test setting configuration values."""
        from web_scraper.config.config_loader import ConfigLoader

        loader = ConfigLoader()

        loader.set("scraping.timeout", 60)
        value = loader.get("scraping.timeout")

        assert value == 60


class TestExporters:
    """Test data exporters."""

    def test_json_exporter(self, tmp_path):
        """Test JSON exporter."""
        from web_scraper.exporters.json_exporter import JSONExporter

        output_file = tmp_path / "test.json"
        exporter = JSONExporter(str(output_file))

        data = [
            {"name": "Item 1", "value": 100},
            {"name": "Item 2", "value": 200}
        ]

        exporter.export(data)

        assert output_file.exists()

    def test_csv_exporter(self, tmp_path):
        """Test CSV exporter."""
        from web_scraper.exporters.csv_exporter import CSVExporter

        output_file = tmp_path / "test.csv"
        exporter = CSVExporter(str(output_file))

        data = [
            {"name": "Item 1", "value": 100},
            {"name": "Item 2", "value": 200}
        ]

        exporter.export(data)

        assert output_file.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
