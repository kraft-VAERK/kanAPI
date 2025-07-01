"""SQLiteConnection class for managing SQLite database connections and operations."""

import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple


class SQLiteConnection:
    """A class to handle SQLite database connections and operations."""

    def __init__(self, db_path: str) -> None:
        """Initialize the SQLite connection.

        Args:
            db_path: Path to the SQLite database file

        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect(self) -> None:
        """Establish a connection to the SQLite database."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.conn = sqlite3.connect(self.db_path)
        # Return rows as dictionaries
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def disconnect(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def execute(self, query: str, params: Tuple = ()) -> None:
        """Execute a query without returning results.

        Args:
            query: SQL query to execute
            params: Parameters for the query

        """
        if not self.conn:
            self.connect()
        self.cursor.execute(query, params)
        self.conn.commit()

    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """Execute a query and fetch one result.

        Args:
            query: SQL query to execute
            params: Parameters for the query

        Returns:
            A single row as a dictionary or None if no results

        """
        if not self.conn:
            self.connect()
        self.cursor.execute(query, params)
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def fetch_all(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Execute a query and fetch all results.

        Args:
            query: SQL query to execute
            params: Parameters for the query

        Returns:
            List of rows as dictionaries

        """
        if not self.conn:
            self.connect()
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def __enter__(self) -> "SQLiteConnection":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.disconnect()
