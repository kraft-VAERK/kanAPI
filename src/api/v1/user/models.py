"""SQLAlchemy ORM model for User table."""

import uuid

import pydantic
from sqlalchemy import Column, String
from sqlalchemy.orm import Session

from src.api.db.database import Base


class UserDB(Base):
    """SQLAlchemy ORM model for User table."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    full_name = Column(String, nullable=True)
    password = Column(String, nullable=False)
    is_active = Column(String, default=True)


class User(pydantic.BaseModel):
    """Pydantic model for User."""

    id: str | None = pydantic.Field(
        default=None,
        description="Auto-generated UUID by PostgreSQL",
    )
    username: str
    email: str
    full_name: str | None = None
    password: str | None = None
    is_active: bool = True

    class Config:
        """Pydantic config."""

        from_attributes = True  # Allows converting SQLAlchemy model to Pydantic model

    def __str__(self) -> str:
        """Return string representation of the User model."""
        return f"User(id={self.id}, username={self.username}, email={self.email}, \
            full_name={self.full_name}, is_active={self.is_active})"

    def __repr__(self) -> str:
        """Return string representation of the User model for debugging."""
        return (
            f"UserDB(id={self.id}, username={self.username}, email={self.email}, "
            f"full_name={self.full_name}, is_active={self.is_active})"
        )

    def __hash__(self) -> int:
        """Hash function for the User model."""
        return hash((self.id, self.username, self.email, self.full_name, self.is_active))

    def hash_password(self, password: str) -> str:
        """Hash the password using a secure hashing algorithm."""
        import hashlib

        return hashlib.sha256(password.encode()).hexdigest()

    def validate_password(self, password: str, db_password: str) -> bool:
        """Validate the provided password against the stored hashed password."""
        return db_password == self.hash_password(password)


class UserCreate(pydantic.BaseModel):
    """Pydantic model for creating a new User."""

    username: str
    email: str
    password: str
    full_name: str | None = None

    class Config:
        """Pydantic config."""

        from_attributes = True  # Allows converting SQLAlchemy model to Pydantic model


def db_create_user(db: Session, user_create: UserCreate) -> "User":
    """Create a new user in the database.

    Args:
        db: SQLAlchemy database session
        user_create: User creation data containing username, email, password, and optional full name

    Returns:
        User: Created user object

    """
    try:
        user_db = UserDB(
            id=str(uuid.uuid4()),
            username=user_create.username,
            email=user_create.email,
            full_name=user_create.full_name,
            password=User.hash_password(User, user_create.password),
            is_active=True,
        )

        db.add(user_db)
        db.commit()
        db.refresh(user_db)

        return User.model_validate(user_db)
    except Exception as e:
        print(f"Error creating user: {e}")
        db.rollback()
        raise
    finally:
        db.close()
