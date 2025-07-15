"""Database connection module for SQLAlchemy."""

from configparser import ConfigParser
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# Create a base class for declarative models
Base = declarative_base()


def load_config(filename: str = "database.ini", section: str = "postgresql") -> dict:
    """Load database configuration from a file."""
    parser = ConfigParser()
    parser.read(filename)
    # get section, default to postgresql
    config = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            config[param[0]] = param[1]
    else:
        raise Exception(
            f"Section {section} not found in the {filename} file",
        )
    return config


# Load database configuration
config = load_config()

# Create SQLAlchemy engine and session factory
DATABASE_URL = (
    f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Create all tables defined in models."""
    Base.metadata.create_all(bind=engine)
