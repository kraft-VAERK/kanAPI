"""kanAPI - A Kanban API for managing tasks and projects."""

from .config import load_config
from .create_database import create_database
from .create_tables import create_tables
from .postgres import PostgresDB

config = load_config()
PostgresDB.connect(PostgresDB, config)
create_database("postgres")
create_tables()  # Ensure tables are created when the module is imported
