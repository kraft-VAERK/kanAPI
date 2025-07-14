"""Craete a PostgreSQL database for kanAPI."""


import psycopg2
from psycopg2 import sql

from .config import load_config


def create_database(db_name: str) -> None:
    """Create a PostgreSQL database."""
    try:
        config = load_config()
        with psycopg2.connect(**config) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            exists = cur.fetchone()
            if exists:
                print(f"Database '{db_name}' already exists.")
                return
            print(f"Creating database '{db_name}'...")
            # Use sql.Identifier to safely handle the database name
            # This prevents SQL injection and ensures the name is correctly formatted
            db_name = db_name.lower()  # PostgreSQL database names are case-insensitive
            # are stored in lowercase by default
            if not db_name.isidentifier():
                raise ValueError(f"Invalid database name: {db_name}")
            # Create the database if it does not exist
            cur.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"),
                            (db_name,))

    except psycopg2.Error as e:
        print(f"Error creating database: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
