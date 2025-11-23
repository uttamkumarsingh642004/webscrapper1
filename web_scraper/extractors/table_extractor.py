"""
Table extraction utilities.

Provides methods to extract and parse HTML tables.
"""

from typing import List, Dict, Optional, Any, Union
from bs4 import BeautifulSoup, Tag
import pandas as pd


class TableExtractor:
    """
    Extract and parse HTML tables.

    Supports various table formats and provides conversion
    to different data structures.
    """

    def __init__(self, clean_whitespace: bool = True):
        """
        Initialize table extractor.

        Args:
            clean_whitespace: Whether to clean whitespace in cell values
        """
        self.clean_whitespace = clean_whitespace

    def extract_tables(self, html: str) -> List[List[List[str]]]:
        """
        Extract all tables from HTML.

        Args:
            html: HTML content

        Returns:
            List of tables, where each table is a list of rows,
            and each row is a list of cell values
        """
        soup = BeautifulSoup(html, "lxml")
        tables = []

        for table_tag in soup.find_all("table"):
            table_data = self._extract_table_data(table_tag)
            if table_data:
                tables.append(table_data)

        return tables

    def extract_table_by_index(self, html: str, index: int = 0) -> Optional[List[List[str]]]:
        """
        Extract a specific table by index.

        Args:
            html: HTML content
            index: Table index (0-based)

        Returns:
            Table data or None if index out of range
        """
        tables = self.extract_tables(html)

        if 0 <= index < len(tables):
            return tables[index]

        return None

    def extract_table_by_selector(self, html: str, selector: str) -> Optional[List[List[str]]]:
        """
        Extract table matching CSS selector.

        Args:
            html: HTML content
            selector: CSS selector

        Returns:
            Table data or None if not found
        """
        soup = BeautifulSoup(html, "lxml")
        table_tag = soup.select_one(selector)

        if table_tag and table_tag.name == "table":
            return self._extract_table_data(table_tag)

        return None

    def _extract_table_data(self, table_tag: Tag) -> List[List[str]]:
        """
        Extract data from table tag.

        Args:
            table_tag: BeautifulSoup table tag

        Returns:
            List of rows, where each row is a list of cell values
        """
        rows = []

        # Extract header rows from thead
        thead = table_tag.find("thead")
        if thead:
            for tr in thead.find_all("tr"):
                row_data = self._extract_row_data(tr)
                if row_data:
                    rows.append(row_data)

        # Extract body rows from tbody
        tbody = table_tag.find("tbody")
        if tbody:
            for tr in tbody.find_all("tr"):
                row_data = self._extract_row_data(tr)
                if row_data:
                    rows.append(row_data)
        else:
            # If no tbody, extract all tr tags
            for tr in table_tag.find_all("tr"):
                # Skip if already processed in thead
                if thead and tr.find_parent("thead"):
                    continue

                row_data = self._extract_row_data(tr)
                if row_data:
                    rows.append(row_data)

        # Extract footer rows from tfoot
        tfoot = table_tag.find("tfoot")
        if tfoot:
            for tr in tfoot.find_all("tr"):
                row_data = self._extract_row_data(tr)
                if row_data:
                    rows.append(row_data)

        return rows

    def _extract_row_data(self, tr_tag: Tag) -> List[str]:
        """
        Extract data from table row.

        Args:
            tr_tag: BeautifulSoup tr tag

        Returns:
            List of cell values
        """
        cells = []

        for cell in tr_tag.find_all(["td", "th"]):
            cell_value = cell.get_text()

            if self.clean_whitespace:
                cell_value = " ".join(cell_value.split())

            # Handle colspan
            colspan = cell.get("colspan")
            if colspan:
                try:
                    colspan = int(colspan)
                    cells.extend([cell_value] * colspan)
                except (ValueError, TypeError):
                    cells.append(cell_value)
            else:
                cells.append(cell_value)

        return cells

    def extract_tables_as_dicts(self, html: str, has_header: bool = True) -> List[List[Dict[str, str]]]:
        """
        Extract tables as lists of dictionaries.

        Args:
            html: HTML content
            has_header: Whether first row is header

        Returns:
            List of tables, where each table is a list of row dictionaries
        """
        tables = self.extract_tables(html)
        result = []

        for table in tables:
            if not table:
                continue

            if has_header and len(table) > 1:
                headers = table[0]
                rows = table[1:]

                table_dicts = []
                for row in rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        header = headers[i] if i < len(headers) else f"Column_{i}"
                        row_dict[header] = value
                    table_dicts.append(row_dict)

                result.append(table_dicts)
            else:
                # No header, use column indices
                table_dicts = []
                for row in table:
                    row_dict = {f"Column_{i}": value for i, value in enumerate(row)}
                    table_dicts.append(row_dict)
                result.append(table_dicts)

        return result

    def extract_table_to_dataframe(self, html: str, index: int = 0, has_header: bool = True) -> Optional[pd.DataFrame]:
        """
        Extract table as pandas DataFrame.

        Args:
            html: HTML content
            index: Table index
            has_header: Whether first row is header

        Returns:
            pandas DataFrame or None
        """
        table = self.extract_table_by_index(html, index)

        if not table:
            return None

        if has_header and len(table) > 1:
            df = pd.DataFrame(table[1:], columns=table[0])
        else:
            df = pd.DataFrame(table)

        return df

    def extract_all_tables_to_dataframes(self, html: str, has_header: bool = True) -> List[pd.DataFrame]:
        """
        Extract all tables as pandas DataFrames.

        Args:
            html: HTML content
            has_header: Whether first row is header

        Returns:
            List of pandas DataFrames
        """
        tables = self.extract_tables(html)
        dataframes = []

        for table in tables:
            if not table:
                continue

            if has_header and len(table) > 1:
                df = pd.DataFrame(table[1:], columns=table[0])
            else:
                df = pd.DataFrame(table)

            dataframes.append(df)

        return dataframes

    def extract_table_with_attributes(self, html: str, selector: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract tables with their HTML attributes.

        Args:
            html: HTML content
            selector: Optional CSS selector for specific table

        Returns:
            List of dictionaries containing table data and attributes
        """
        soup = BeautifulSoup(html, "lxml")

        if selector:
            table_tags = soup.select(selector)
        else:
            table_tags = soup.find_all("table")

        tables_with_attrs = []

        for table_tag in table_tags:
            table_info = {
                "data": self._extract_table_data(table_tag),
                "attributes": {
                    "class": table_tag.get("class", []),
                    "id": table_tag.get("id"),
                    "border": table_tag.get("border"),
                    "cellspacing": table_tag.get("cellspacing"),
                    "cellpadding": table_tag.get("cellpadding"),
                },
                "caption": None,
                "summary": table_tag.get("summary")
            }

            # Extract caption if present
            caption = table_tag.find("caption")
            if caption:
                table_info["caption"] = caption.get_text(strip=True)

            tables_with_attrs.append(table_info)

        return tables_with_attrs

    def extract_nested_tables(self, html: str) -> Dict[str, Any]:
        """
        Extract nested tables with their hierarchy.

        Args:
            html: HTML content

        Returns:
            Dictionary representing table hierarchy
        """
        soup = BeautifulSoup(html, "lxml")
        tables = soup.find_all("table")

        # Build hierarchy
        table_hierarchy = []

        for table in tables:
            # Check if this table is nested in another
            parent_table = table.find_parent("table")

            if not parent_table:
                # Top-level table
                table_data = {
                    "data": self._extract_table_data(table),
                    "nested_tables": self._extract_nested_from_table(table)
                }
                table_hierarchy.append(table_data)

        return {"tables": table_hierarchy}

    def _extract_nested_from_table(self, table_tag: Tag) -> List[Dict[str, Any]]:
        """
        Extract nested tables from a table.

        Args:
            table_tag: BeautifulSoup table tag

        Returns:
            List of nested table data
        """
        nested_tables = []

        # Find direct child tables (not in nested tables)
        for nested_table in table_tag.find_all("table"):
            # Make sure it's a direct descendant, not in another nested table
            if nested_table.find_parent("table") == table_tag:
                nested_data = {
                    "data": self._extract_table_data(nested_table),
                    "nested_tables": self._extract_nested_from_table(nested_table)
                }
                nested_tables.append(nested_data)

        return nested_tables

    def find_table_by_header(self, html: str, header_text: str) -> Optional[List[List[str]]]:
        """
        Find table containing specific header text.

        Args:
            html: HTML content
            header_text: Text to search for in headers

        Returns:
            Table data or None
        """
        soup = BeautifulSoup(html, "lxml")

        for table_tag in soup.find_all("table"):
            # Check thead
            thead = table_tag.find("thead")
            if thead:
                if header_text.lower() in thead.get_text().lower():
                    return self._extract_table_data(table_tag)

            # Check first row th tags
            first_row = table_tag.find("tr")
            if first_row:
                headers = first_row.find_all("th")
                for header in headers:
                    if header_text.lower() in header.get_text().lower():
                        return self._extract_table_data(table_tag)

        return None

    def extract_table_statistics(self, table_data: List[List[str]]) -> Dict[str, Any]:
        """
        Get statistics about a table.

        Args:
            table_data: Table data (list of rows)

        Returns:
            Dictionary with table statistics
        """
        if not table_data:
            return {
                "num_rows": 0,
                "num_columns": 0,
                "is_empty": True
            }

        num_rows = len(table_data)
        num_columns = max(len(row) for row in table_data) if table_data else 0

        # Check for consistency
        column_counts = [len(row) for row in table_data]
        is_rectangular = len(set(column_counts)) == 1

        # Calculate empty cells
        total_cells = sum(column_counts)
        empty_cells = sum(1 for row in table_data for cell in row if not cell.strip())

        return {
            "num_rows": num_rows,
            "num_columns": num_columns,
            "is_rectangular": is_rectangular,
            "column_counts": column_counts,
            "total_cells": total_cells,
            "empty_cells": empty_cells,
            "empty_cell_percentage": (empty_cells / total_cells * 100) if total_cells > 0 else 0,
            "is_empty": num_rows == 0
        }
