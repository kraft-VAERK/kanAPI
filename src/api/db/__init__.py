"""kanAPI - A Kanban API for managing tasks and projects."""

from .database import create_tables

# Initialize database tables if they don't exist
create_tables()
