"""user.py - FastAPI router for user-related endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.db.database import get_db

from .models import User, db_create_user

router = APIRouter(prefix="/user", tags=["User"])


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
