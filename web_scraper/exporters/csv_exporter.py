"""
CSV data exporter.

Exports scraped data to CSV format with various options.
"""

import csv
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
import pandas as pd

from web_scraper.exporters.base_exporter import BaseExporter


class CSVExporter(BaseExporter):
    """
    Export data to CSV format.

    Supports custom delimiters, quoting, and incremental export.
    """

    def __init__(
        self,
        output_file: str,
        delimiter: str = ",",
        quoting: str = "minimal",
        include_headers: bool = True,
        **kwargs
    ):
        """
        Initialize CSV exporter.

        Args:
            output_file: Path to output CSV file
            delimiter: Field delimiter
            quoting: Quoting style (minimal, all, nonnumeric, none)
            include_headers: Whether to include header row
            **kwargs: Additional arguments
        """
        super().__init__(output_file, **kwargs)
        self.delimiter = delimiter
        self.include_headers = include_headers

        # Map quoting string to csv constant
        quoting_map = {
            "minimal": csv.QUOTE_MINIMAL,
            "all": csv.QUOTE_ALL,
            "nonnumeric": csv.QUOTE_NONNUMERIC,
            "none": csv.QUOTE_NONE
        }
        self.quoting = quoting_map.get(quoting.lower(), csv.QUOTE_MINIMAL)

    def export(self, data: List[Dict[str, Any]]) -> None:
        """
        Export data to CSV file.

        Args:
            data: List of data dictionaries to export
        """
        if not self.validate_data(data):
            raise ValueError("Invalid data format for CSV export")

        # Clean data
        cleaned_data = self.clean_data(
            data,
            remove_duplicates=self.kwargs.get("remove_duplicates", False),
            duplicate_key=self.kwargs.get("duplicate_key", "url")
        )

        if not cleaned_data:
            # Create empty file
            self.output_file.touch()
            return

        # Flatten nested dictionaries
        flattened_data = [self._flatten_dict(item) for item in cleaned_data]

        # Get all unique field names
        fieldnames = self._get_fieldnames(flattened_data)

        # Write to CSV
        with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                delimiter=self.delimiter,
                quoting=self.quoting,
                extrasaction='ignore'
            )

            if self.include_headers:
                writer.writeheader()

            writer.writerows(flattened_data)

    def append(self, data: Dict[str, Any]) -> None:
        """
        Append single item to CSV file.

        Args:
            data: Data dictionary to append
        """
        # Flatten data
        flattened = self._flatten_dict(data)

        # Check if file exists
        file_exists = self.output_file.exists()

        # Get existing fieldnames if file exists
        if file_exists and self.include_headers:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=self.delimiter)
                existing_fieldnames = reader.fieldnames or []

            # Merge fieldnames
            new_fields = set(flattened.keys()) - set(existing_fieldnames)

            if new_fields:
                # Need to rewrite file with new fields
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f, delimiter=self.delimiter)
                    existing_data = list(reader)

                fieldnames = list(existing_fieldnames) + list(new_fields)
                existing_data.append(flattened)

                with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=fieldnames,
                        delimiter=self.delimiter,
                        quoting=self.quoting,
                        extrasaction='ignore'
                    )
                    writer.writeheader()
                    writer.writerows(existing_data)
            else:
                # Just append
                with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=existing_fieldnames,
                        delimiter=self.delimiter,
                        quoting=self.quoting,
                        extrasaction='ignore'
                    )
                    writer.writerow(flattened)
        else:
            # New file or no headers
            fieldnames = list(flattened.keys())

            with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=fieldnames,
                    delimiter=self.delimiter,
                    quoting=self.quoting,
                    extrasaction='ignore'
                )

                if not file_exists and self.include_headers:
                    writer.writeheader()

                writer.writerow(flattened)

    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
        """
        Flatten nested dictionary.

        Args:
            d: Dictionary to flatten
            parent_key: Parent key for nested items
            sep: Separator for nested keys

        Returns:
            Flattened dictionary
        """
        items = []

        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k

            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Convert list to string representation
                items.append((new_key, str(v)))
            else:
                items.append((new_key, v))

        return dict(items)

    def _get_fieldnames(self, data: List[Dict[str, Any]]) -> List[str]:
        """
        Get all unique field names from data.

        Args:
            data: List of dictionaries

        Returns:
            List of field names
        """
        fieldnames: Set[str] = set()

        for item in data:
            fieldnames.update(item.keys())

        return sorted(fieldnames)


class ExcelExporter(BaseExporter):
    """
    Export data to Excel format.

    Uses pandas and openpyxl for Excel export.
    """

    def __init__(
        self,
        output_file: str,
        sheet_name: str = "Sheet1",
        **kwargs
    ):
        """
        Initialize Excel exporter.

        Args:
            output_file: Path to output Excel file
            sheet_name: Name of the Excel sheet
            **kwargs: Additional arguments
        """
        super().__init__(output_file, **kwargs)
        self.sheet_name = sheet_name

    def export(self, data: List[Dict[str, Any]]) -> None:
        """
        Export data to Excel file.

        Args:
            data: List of data dictionaries to export
        """
        if not self.validate_data(data):
            raise ValueError("Invalid data format for Excel export")

        # Clean data
        cleaned_data = self.clean_data(
            data,
            remove_duplicates=self.kwargs.get("remove_duplicates", False),
            duplicate_key=self.kwargs.get("duplicate_key", "url")
        )

        if not cleaned_data:
            # Create empty DataFrame
            df = pd.DataFrame()
        else:
            # Convert to DataFrame
            df = pd.DataFrame(cleaned_data)

        # Export to Excel
        with pd.ExcelWriter(self.output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=self.sheet_name, index=False)

    def append(self, data: Dict[str, Any]) -> None:
        """
        Append single item to Excel file.

        Args:
            data: Data dictionary to append
        """
        # Read existing data if file exists
        if self.output_file.exists():
            existing_df = pd.read_excel(self.output_file, sheet_name=self.sheet_name)
            new_df = pd.DataFrame([data])
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = pd.DataFrame([data])

        # Write back
        with pd.ExcelWriter(self.output_file, engine='openpyxl') as writer:
            combined_df.to_excel(writer, sheet_name=self.sheet_name, index=False)

    def export_multiple_sheets(self, data_dict: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        Export multiple datasets to different sheets.

        Args:
            data_dict: Dictionary mapping sheet names to data lists
        """
        with pd.ExcelWriter(self.output_file, engine='openpyxl') as writer:
            for sheet_name, data in data_dict.items():
                if not data:
                    df = pd.DataFrame()
                else:
                    df = pd.DataFrame(data)

                df.to_excel(writer, sheet_name=sheet_name, index=False)
