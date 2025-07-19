"""user.py - FastAPI router for user-related endpoints."""

import os
from typing import Annotated, List, Optional

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.db.database import get_db

from .models import User, UserDB, db_create_user, db_delete_user

load_dotenv()  # Load environment variables from .env file

router = APIRouter(prefix="/user", tags=["User"])

# Secret key for JWT - should match the one in auth.py
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM")
if not SECRET_KEY or not ALGORITHM:
    raise ValueError(
        "JWT_SECRET_KEY and JWT_ALGORITHM must be set in the environment variables.",
    )


# Internal authentication function for this module
async def get_current_user_from_cookie_internal(
    db: Session,
    session: Optional[str] = None,
) -> User:
    """Get the current user from the session cookie."""
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(session, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token",
            )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
        ) from e

    user_db = db.query(UserDB).filter(UserDB.username == username).first()
    if user_db is None:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    return User.model_validate(user_db)


# Dependency for getting the current user from a cookie
async def get_user_from_cookie(
    db: Session = Depends(get_db),  # noqa: B008
    session: Optional[str] = Cookie(default=None),
) -> User:
    """Get the current user from the session cookie."""
    return await get_current_user_from_cookie_internal(db, session)


@router.post("/create", response_model=User)
async def create_user(
    user: User,
    db: Session = Depends(get_db),  # noqa: B008
) -> User:
    """Create a new user."""
    # print(f"Creating user: {user}")

    try:
        new_user = db_create_user(db=db, user_create=user)
        return new_user
    except Exception as e:
        print(f"Error creating user: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error creating user",
        ) from e


@router.get("/delete", response_model=bool)
async def delete_user(
    user_delete: User,
    db: Session = Depends(get_db),  # noqa: B008
) -> bool:
    """Delete a user by user_id or email."""
    # print(f"Deleting user: {user_delete}")

    try:
        deleted = db_delete_user(db=db, user_delete=user_delete)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )
        return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error deleting user",
        ) from e


@router.get("/all", response_model=List[User])
async def get_all_users(
    current_user: Annotated[User, Depends(get_user_from_cookie)],
    db: Session = Depends(get_db),  # noqa: B008
) -> List[User]:
    """Get all users. Requires authentication."""
    try:
        # Only proceed if the user is authenticated (handled by the dependency)
        print(f"Request by authenticated user: {current_user.username}")

        users = db.query(UserDB).all()
        return [User.model_validate(user) for user in users]
    except Exception as e:
        print(f"Error fetching users: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error fetching users",
        ) from e
