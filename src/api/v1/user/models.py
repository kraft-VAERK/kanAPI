"""SQLAlchemy ORM model for User table."""

import logging
from typing import Optional

import pydantic
from fastapi import HTTPException
from pydantic import ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.api.db.database import Base

logger = logging.getLogger(__name__)


class UserDB(Base):
    """SQLAlchemy ORM model for User table."""

    __tablename__ = "users"

    username = Column(String, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True)
    full_name = Column(String, nullable=True)
    password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    parent_id = Column(String, ForeignKey('users.username', ondelete='CASCADE', onupdate='CASCADE'), nullable=True)


class User(pydantic.BaseModel):
    """Pydantic model for User."""

    model_config = ConfigDict(from_attributes=True)

    username: str
    email: str
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = True
    is_admin: Optional[bool] = False
    parent_id: Optional[str] = None

    @field_validator('parent_id', mode='before')
    @classmethod
    def coerce_parent_id(cls, v: object) -> Optional[str]:
        """Convert UUID objects to str (handles old DB schema during migration)."""
        return str(v) if v is not None else None

    def __str__(self) -> str:
        """Return string representation of the User model."""
        return f"User(username={self.username}, email={self.email}, \
            full_name={self.full_name}, is_active={self.is_active})"

    def __repr__(self) -> str:
        """Return string representation of the User model for debugging."""
        return (
            f"UserDB(username={self.username}, email={self.email}, "
            f"full_name={self.full_name}, is_active={self.is_active})"
        )

    def __hash__(self) -> int:
        """Hash function for the User model."""
        return hash((self.username, self.email, self.full_name, self.is_active))

    def hash_password(self, password: str) -> str:
        """Hash the password using bcrypt."""
        import bcrypt

        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def validate_password(self, password: str, db_password: str) -> bool:
        """Validate the provided password against the stored hashed password."""
        import bcrypt

        return bcrypt.checkpw(password.encode(), db_password.encode())


class UserCreate(pydantic.BaseModel):
    """Pydantic model for creating a new User."""

    model_config = ConfigDict(from_attributes=True)

    username: Optional[str] = None  # auto-generated if not provided
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)
    is_admin: Optional[bool] = False
    parent_id: Optional[str] = None


class UserDelete(pydantic.BaseModel):
    """Pydantic model for deleting a User."""

    model_config = ConfigDict(from_attributes=True)

    username: Optional[str] = None
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


def db_update_user(db: Session, username: str, user_update: UserUpdate) -> Optional["User"]:
    """Update an existing user in the database."""
    try:
        user_db = db.query(UserDB).filter(UserDB.username == username).first()
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
        logger.exception("Database error: %s", e)
        raise HTTPException(status_code=500, detail="Database error") from e


def db_create_user(db: Session, user_create: UserCreate) -> "User":
    """Create a new user in the database."""
    import re
    try:
        if user_create.username:
            username = user_create.username
        else:
            base = re.sub(r'[^a-z0-9.]', '.', user_create.email.split('@')[0].lower())
            base = re.sub(r'\.+', '.', base).strip('.')
            # append short suffix to avoid collisions
            from uuid_extensions import uuid7
            username = f'{base}.{str(uuid7()).replace("-", "")[-4:]}'
        user_db = UserDB(
            username=username,
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
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def db_delete_user(db: Session, user_delete: UserDelete) -> bool:
    """Delete a user from the database."""
    if not user_delete.username and not user_delete.email:
        raise ValueError("username or email must be provided")
    try:
        if user_delete.email:
            user_db = db.query(UserDB).filter(UserDB.email == user_delete.email).first()
        else:
            user_db = db.query(UserDB).filter(UserDB.username == user_delete.username).first()
        if not user_db:
            return False

        db.delete(user_db)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
