"""
Logging utility for the web scraper.

Provides comprehensive logging with file and console output,
different verbosity levels, and structured log formatting.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler


class ScraperLogger:
    """
    Custom logger for web scraping operations.

    Supports multiple log levels, file and console output,
    and automatic log rotation.
    """

    _instances = {}

    def __new__(cls, name: str = "WebScraper"):
        """Singleton pattern to ensure one logger per name."""
        if name not in cls._instances:
            cls._instances[name] = super().__new__(cls)
        return cls._instances[name]

    def __init__(
        self,
        name: str = "WebScraper",
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        log_to_console: bool = True,
        log_format: Optional[str] = None,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        """
        Initialize the logger.

        Args:
            name: Logger name
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Path to log file (optional)
            log_to_console: Whether to output logs to console
            log_format: Custom log format string
            max_bytes: Maximum size of log file before rotation
            backup_count: Number of backup log files to keep
        """
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Clear existing handlers
        self.logger.handlers.clear()

        # Set log format
        if log_format is None:
            log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        formatter = logging.Formatter(log_format)

        # Add console handler
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # Add file handler with rotation
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(message, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback."""
        self.logger.exception(message, **kwargs)

    def set_level(self, level: str) -> None:
        """
        Change the logging level.

        Args:
            level: New logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger.setLevel(getattr(logging, level.upper()))


def get_logger(
    name: str = "WebScraper",
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_to_console: bool = True
) -> ScraperLogger:
    """
    Get or create a logger instance.

    Args:
        name: Logger name
        log_level: Logging level
        log_file: Path to log file
        log_to_console: Whether to output to console

    Returns:
        ScraperLogger instance
    """
    return ScraperLogger(
        name=name,
        log_level=log_level,
        log_file=log_file,
        log_to_console=log_to_console
    )
