"""Postgress interface for kanAPI."""

import psycopg2  # type: ignore


class PostgresDB:
    """Postgres database interface for kanAPI."""

    def __init__(self) -> None:
        """Initialize the PostgresDB instance."""
        self.connection = None
        self.cursor = None
        self.connect()

    def connect(self, config: dict) -> None:
        """Connect to the PostgreSQL database server."""
        try:
            # connecting to the PostgreSQL server
            with psycopg2.connect(**config) as conn:
                print("Connected to the PostgreSQL server.")
                return conn
        except (psycopg2.DatabaseError, Exception) as error:
            print(error)

    def close(self) -> None:
        """Close the database connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        self.connection = None
        self.cursor = None
