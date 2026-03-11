"""SQLAlchemy ORM model for User table."""

from typing import Optional

import pydantic
from fastapi import HTTPException
from pydantic import ConfigDict
from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from uuid_extensions import uuid7

from src.api.db.database import Base


class UserDB(Base):
    """SQLAlchemy ORM model for User table."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    full_name = Column(String, nullable=True)
    password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    parent_id = Column(UUID(as_uuid=False), ForeignKey('users.id', ondelete='CASCADE'), nullable=True)


class User(pydantic.BaseModel):
    """Pydantic model for User."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = pydantic.Field(
        default=None,
        description="Auto-generated UUID by PostgreSQL",
    )
    username: str
    email: str
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = True
    is_admin: Optional[bool] = False
    parent_id: Optional[str] = None

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

    model_config = ConfigDict(from_attributes=True)

    username: str
    email: str
    password: str
    full_name: Optional[str] = None
    is_admin: Optional[bool] = False
    parent_id: Optional[str] = None


class UserDelete(pydantic.BaseModel):
    """Pydantic model for deleting a User."""

    model_config = ConfigDict(from_attributes=True)

    user_id: Optional[str] = None
    email: Optional[str] = None


class UserUpdate(pydantic.BaseModel):
    """Pydantic model for updating a User. All fields are optional."""

    model_config = ConfigDict(from_attributes=True)

    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    parent_id: Optional[str] = None


def db_update_user(db: Session, user_id: str, user_update: UserUpdate) -> Optional["User"]:
    """Update an existing user in the database.

    Args:
        db: SQLAlchemy database session
        user_id: ID of the user to update
        user_update: Fields to update (only non-None values are applied)

    Returns:
        User: Updated user object, or None if not found

    """
    try:
        user_db = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user_db:
            return None

        updates = user_update.model_dump(exclude_none=True)
        if 'password' in updates:
            updates['password'] = User.hash_password(User, updates['password'])

        for field, value in updates.items():
            setattr(user_db, field, value)

        db.commit()
        db.refresh(user_db)
        return User.model_validate(user_db)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Database error: {e!s}') from e


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
            id=str(uuid7()),
            username=user_create.username,
            email=user_create.email,
            full_name=user_create.full_name,
            password=User.hash_password(User, user_create.password),
            is_active=True,
            is_admin=user_create.is_admin,
            parent_id=user_create.parent_id,
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


def db_delete_user(db: Session, user_delete: UserDelete) -> bool:
    """Delete a user from the database.

    Args:
        db: SQLAlchemy database session
        user_delete: User deletion data containing either user_id or email

    Returns:
        bool: True if user was deleted, False if user was not found

    """
    if not user_delete.user_id and not user_delete.email:
        raise ValueError("user_id or email must be provided")
    if user_delete.email:
        user_db = db.query(UserDB).filter(UserDB.email == user_delete.email).first()
        if not user_db:
            return False
        print(f"User found by email: {user_db}")
    try:
        user_db = db.query(UserDB).filter(UserDB.id == user_delete.user_id).first()
        if not user_db:
            return False

        db.delete(user_db)
        db.commit()
        return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        db.rollback()
        raise
    finally:
        db.close()
