"""Module creates the necessary tables in the PostgreSQL database."""

import psycopg2

from .config import load_config


def create_tables() -> None:
    """Create tables in the PostgreSQL database."""
    commands = [
        """
        CREATE TABLE IF NOT EXISTS cases (
            id SERIAL PRIMARY KEY,
            deleted BOOLEAN NOT NULL DEFAULT FALSE,
            responsible_person VARCHAR(100) NOT NULL,
            status VARCHAR(50) NOT NULL,
            customer VARCHAR(100) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            title VARCHAR(255),
            description TEXT
        )
        """,
    ]
    try:
        config = load_config()
        with psycopg2.connect(**config) as conn, conn.cursor() as cur:
            # execute the CREATE TABLE statement
            for command in commands:
            # Skip table creation if it already exists (for CREATE TABLE commands only)
                if command.strip().upper().startswith("CREATE TABLE"):
                    table_name = (command.split("CREATE TABLE")[1]
                                 .strip().split(" ")[0].strip("("))
                    query = f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = '{table_name}'
                        )
                    """  # noqa: W291
                    cur.execute(query)
                    if cur.fetchone()[0]:
                        print(f"Table {table_name} already exists, skipping creation.")
                        continue
                cur.execute(command)
    except (psycopg2.DatabaseError, Exception) as error:
        print(error)
