"""
Base exporter abstract class.

Defines the interface for all data exporters.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path


class BaseExporter(ABC):
    """
    Abstract base class for data exporters.

    Provides common functionality for exporting scraped data
    to various formats.
    """

    def __init__(self, output_file: str, **kwargs):
        """
        Initialize exporter.

        Args:
            output_file: Path to output file
            **kwargs: Additional exporter-specific arguments
        """
        self.output_file = Path(output_file)
        self.kwargs = kwargs

        # Create output directory if it doesn't exist
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def export(self, data: List[Dict[str, Any]]) -> None:
        """
        Export data to file.

        Args:
            data: List of data dictionaries to export
        """
        pass

    @abstractmethod
    def append(self, data: Dict[str, Any]) -> None:
        """
        Append single item to export file.

        Args:
            data: Data dictionary to append
        """
        pass

    def validate_data(self, data: List[Dict[str, Any]]) -> bool:
        """
        Validate data before export.

        Args:
            data: Data to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(data, list):
            return False

        if not data:
            return True  # Empty data is valid

        # Check if all items are dictionaries
        return all(isinstance(item, dict) for item in data)

    def clean_data(self, data: List[Dict[str, Any]], remove_duplicates: bool = False, duplicate_key: str = "url") -> List[Dict[str, Any]]:
        """
        Clean data before export.

        Args:
            data: Data to clean
            remove_duplicates: Whether to remove duplicates
            duplicate_key: Key to use for duplicate detection

        Returns:
            Cleaned data
        """
        if not data:
            return data

        cleaned = data

        # Remove duplicates
        if remove_duplicates:
            seen = set()
            unique_data = []

            for item in cleaned:
                key_value = item.get(duplicate_key)
                if key_value and key_value not in seen:
                    seen.add(key_value)
                    unique_data.append(item)
                elif not key_value:
                    unique_data.append(item)

            cleaned = unique_data

        return cleaned

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        return False
