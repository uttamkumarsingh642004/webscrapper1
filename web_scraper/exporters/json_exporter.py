"""
JSON data exporter.

Exports scraped data to JSON format with various options.
"""

import json
from typing import Any, Dict, List, Optional
from pathlib import Path

from web_scraper.exporters.base_exporter import BaseExporter


class JSONExporter(BaseExporter):
    """
    Export data to JSON format.

    Supports pretty printing, custom encoding, and incremental export.
    """

    def __init__(
        self,
        output_file: str,
        indent: int = 2,
        ensure_ascii: bool = False,
        sort_keys: bool = False,
        **kwargs
    ):
        """
        Initialize JSON exporter.

        Args:
            output_file: Path to output JSON file
            indent: Indentation level for pretty printing
            ensure_ascii: Whether to escape non-ASCII characters
            sort_keys: Whether to sort dictionary keys
            **kwargs: Additional arguments
        """
        super().__init__(output_file, **kwargs)
        self.indent = indent
        self.ensure_ascii = ensure_ascii
        self.sort_keys = sort_keys

    def export(self, data: List[Dict[str, Any]]) -> None:
        """
        Export data to JSON file.

        Args:
            data: List of data dictionaries to export
        """
        if not self.validate_data(data):
            raise ValueError("Invalid data format for JSON export")

        # Clean data
        cleaned_data = self.clean_data(
            data,
            remove_duplicates=self.kwargs.get("remove_duplicates", False),
            duplicate_key=self.kwargs.get("duplicate_key", "url")
        )

        # Export to JSON
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(
                cleaned_data,
                f,
                indent=self.indent,
                ensure_ascii=self.ensure_ascii,
                sort_keys=self.sort_keys,
                default=str  # Handle non-serializable objects
            )

    def append(self, data: Dict[str, Any]) -> None:
        """
        Append single item to JSON file.

        Args:
            data: Data dictionary to append
        """
        # Read existing data
        existing_data = []
        if self.output_file.exists():
            try:
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []

        # Append new data
        existing_data.append(data)

        # Write back
        self.export(existing_data)

    def export_jsonl(self, data: List[Dict[str, Any]]) -> None:
        """
        Export data to JSON Lines format (one JSON object per line).

        Args:
            data: List of data dictionaries to export
        """
        if not self.validate_data(data):
            raise ValueError("Invalid data format for JSON Lines export")

        # Clean data
        cleaned_data = self.clean_data(
            data,
            remove_duplicates=self.kwargs.get("remove_duplicates", False),
            duplicate_key=self.kwargs.get("duplicate_key", "url")
        )

        # Export to JSON Lines
        with open(self.output_file, 'w', encoding='utf-8') as f:
            for item in cleaned_data:
                json_line = json.dumps(item, ensure_ascii=self.ensure_ascii, default=str)
                f.write(json_line + '\n')

    def append_jsonl(self, data: Dict[str, Any]) -> None:
        """
        Append single item to JSON Lines file.

        Args:
            data: Data dictionary to append
        """
        with open(self.output_file, 'a', encoding='utf-8') as f:
            json_line = json.dumps(data, ensure_ascii=self.ensure_ascii, default=str)
            f.write(json_line + '\n')


class JSONLExporter(JSONExporter):
    """
    Export data to JSON Lines format.

    Convenience class that defaults to JSON Lines format.
    """

    def export(self, data: List[Dict[str, Any]]) -> None:
        """Export data to JSON Lines format."""
        self.export_jsonl(data)

    def append(self, data: Dict[str, Any]) -> None:
        """Append single item to JSON Lines file."""
        self.append_jsonl(data)
