"""
Database exporters for SQLite and MongoDB.

Exports scraped data to database formats.
"""

import sqlite3
from typing import Any, Dict, List, Optional
from pathlib import Path
import json
from datetime import datetime

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

from web_scraper.exporters.base_exporter import BaseExporter


class SQLiteExporter(BaseExporter):
    """
    Export data to SQLite database.

    Creates tables automatically based on data structure.
    """

    def __init__(
        self,
        output_file: str,
        table_name: str = "scraped_data",
        **kwargs
    ):
        """
        Initialize SQLite exporter.

        Args:
            output_file: Path to SQLite database file
            table_name: Name of the database table
            **kwargs: Additional arguments
        """
        super().__init__(output_file, **kwargs)
        self.table_name = table_name
        self.connection = None

    def _connect(self) -> sqlite3.Connection:
        """
        Connect to SQLite database.

        Returns:
            Database connection
        """
        if self.connection is None:
            self.connection = sqlite3.connect(self.output_file)

        return self.connection

    def _create_table(self, sample_data: Dict[str, Any]) -> None:
        """
        Create table based on sample data.

        Args:
            sample_data: Sample data dictionary to infer schema
        """
        conn = self._connect()
        cursor = conn.cursor()

        # Flatten data
        flattened = self._flatten_dict(sample_data)

        # Build column definitions
        columns = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]

        for key, value in flattened.items():
            # Sanitize column name
            column_name = key.replace(" ", "_").replace("-", "_")

            # Infer type
            if isinstance(value, bool):
                column_type = "BOOLEAN"
            elif isinstance(value, int):
                column_type = "INTEGER"
            elif isinstance(value, float):
                column_type = "REAL"
            else:
                column_type = "TEXT"

            columns.append(f"{column_name} {column_type}")

        # Add timestamp
        columns.append("scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

        # Create table
        create_sql = f"CREATE TABLE IF NOT EXISTS {self.table_name} ({', '.join(columns)})"

        try:
            cursor.execute(create_sql)
            conn.commit()
        except sqlite3.Error as e:
            # Table might already exist with different schema
            pass

    def export(self, data: List[Dict[str, Any]]) -> None:
        """
        Export data to SQLite database.

        Args:
            data: List of data dictionaries to export
        """
        if not self.validate_data(data):
            raise ValueError("Invalid data format for SQLite export")

        # Clean data
        cleaned_data = self.clean_data(
            data,
            remove_duplicates=self.kwargs.get("remove_duplicates", False),
            duplicate_key=self.kwargs.get("duplicate_key", "url")
        )

        if not cleaned_data:
            return

        # Create table based on first item
        self._create_table(cleaned_data[0])

        conn = self._connect()
        cursor = conn.cursor()

        # Insert data
        for item in cleaned_data:
            flattened = self._flatten_dict(item)

            # Prepare insert statement
            columns = list(flattened.keys())
            placeholders = ["?" for _ in columns]

            insert_sql = f"INSERT INTO {self.table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

            try:
                values = [self._serialize_value(v) for v in flattened.values()]
                cursor.execute(insert_sql, values)
            except sqlite3.Error as e:
                # Handle errors (e.g., column doesn't exist)
                # Try to add missing columns
                self._add_missing_columns(flattened)

                # Retry insert
                values = [self._serialize_value(v) for v in flattened.values()]
                cursor.execute(insert_sql, values)

        conn.commit()

    def append(self, data: Dict[str, Any]) -> None:
        """
        Append single item to SQLite database.

        Args:
            data: Data dictionary to append
        """
        self.export([data])

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

            # Sanitize key
            new_key = new_key.replace(" ", "_").replace("-", "_")

            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, (list, tuple)):
                # Convert to JSON string
                items.append((new_key, json.dumps(v)))
            else:
                items.append((new_key, v))

        return dict(items)

    def _serialize_value(self, value: Any) -> Any:
        """
        Serialize value for SQLite storage.

        Args:
            value: Value to serialize

        Returns:
            Serialized value
        """
        if value is None:
            return None
        elif isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, datetime):
            return value.isoformat()
        else:
            return str(value)

    def _add_missing_columns(self, data: Dict[str, Any]) -> None:
        """
        Add missing columns to table.

        Args:
            data: Data with new columns
        """
        conn = self._connect()
        cursor = conn.cursor()

        # Get existing columns
        cursor.execute(f"PRAGMA table_info({self.table_name})")
        existing_columns = {row[1] for row in cursor.fetchall()}

        # Add missing columns
        for key, value in data.items():
            if key not in existing_columns:
                # Infer type
                if isinstance(value, bool):
                    column_type = "BOOLEAN"
                elif isinstance(value, int):
                    column_type = "INTEGER"
                elif isinstance(value, float):
                    column_type = "REAL"
                else:
                    column_type = "TEXT"

                alter_sql = f"ALTER TABLE {self.table_name} ADD COLUMN {key} {column_type}"

                try:
                    cursor.execute(alter_sql)
                except sqlite3.Error:
                    pass

        conn.commit()

    def __del__(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()


class MongoDBExporter(BaseExporter):
    """
    Export data to MongoDB database.

    Stores data in MongoDB collections with flexible schema.
    """

    def __init__(
        self,
        output_file: str,  # Not used, kept for interface compatibility
        mongodb_uri: str = "mongodb://localhost:27017/",
        database_name: str = "web_scraper",
        collection_name: str = "scraped_data",
        **kwargs
    ):
        """
        Initialize MongoDB exporter.

        Args:
            output_file: Not used (kept for interface compatibility)
            mongodb_uri: MongoDB connection URI
            database_name: Database name
            collection_name: Collection name
            **kwargs: Additional arguments
        """
        # Don't call super().__init__ with output_file since we don't need it
        self.output_file = Path(output_file) if output_file else None
        self.kwargs = kwargs

        if not MONGO_AVAILABLE:
            raise ImportError("pymongo is required for MongoDB export. Install it with: pip install pymongo")

        self.mongodb_uri = mongodb_uri
        self.database_name = database_name
        self.collection_name = collection_name
        self.client = None
        self.db = None
        self.collection = None

    def _connect(self) -> None:
        """Connect to MongoDB."""
        if self.client is None:
            self.client = MongoClient(self.mongodb_uri)

            # Test connection
            try:
                self.client.admin.command('ismaster')
            except ConnectionFailure:
                raise ConnectionError(f"Failed to connect to MongoDB at {self.mongodb_uri}")

            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]

    def export(self, data: List[Dict[str, Any]]) -> None:
        """
        Export data to MongoDB.

        Args:
            data: List of data dictionaries to export
        """
        if not self.validate_data(data):
            raise ValueError("Invalid data format for MongoDB export")

        # Clean data
        cleaned_data = self.clean_data(
            data,
            remove_duplicates=self.kwargs.get("remove_duplicates", False),
            duplicate_key=self.kwargs.get("duplicate_key", "url")
        )

        if not cleaned_data:
            return

        # Connect to MongoDB
        self._connect()

        # Add timestamp
        for item in cleaned_data:
            if "scraped_at" not in item:
                item["scraped_at"] = datetime.utcnow()

        # Insert data
        if len(cleaned_data) == 1:
            self.collection.insert_one(cleaned_data[0])
        else:
            self.collection.insert_many(cleaned_data)

    def append(self, data: Dict[str, Any]) -> None:
        """
        Append single item to MongoDB.

        Args:
            data: Data dictionary to append
        """
        self._connect()

        # Add timestamp
        if "scraped_at" not in data:
            data["scraped_at"] = datetime.utcnow()

        self.collection.insert_one(data)

    def create_index(self, field: str, unique: bool = False) -> None:
        """
        Create index on field.

        Args:
            field: Field name to index
            unique: Whether to enforce uniqueness
        """
        self._connect()
        self.collection.create_index(field, unique=unique)

    def query(self, filter_dict: Dict[str, Any], limit: int = 0) -> List[Dict[str, Any]]:
        """
        Query data from MongoDB.

        Args:
            filter_dict: MongoDB filter dictionary
            limit: Maximum number of results (0 for no limit)

        Returns:
            List of matching documents
        """
        self._connect()

        cursor = self.collection.find(filter_dict)

        if limit > 0:
            cursor = cursor.limit(limit)

        return list(cursor)

    def __del__(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
