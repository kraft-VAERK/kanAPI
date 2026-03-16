"""customer.py - FastAPI router for customer-related endpoints."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.db.database import get_db
from src.api.v1.user.models import User

from .models import Customer, CustomerCreate, db_create_customer

router = APIRouter(prefix="/customer", tags=["Customer"])


async def _get_current_user(
    db: Annotated[Session, Depends(get_db)],
    session: Annotated[str | None, Cookie()] = None,
) -> User:
    """Lazy wrapper to avoid circular import with auth module."""
    from src.api.v1.auth.auth import get_current_user_from_cookie

    return await get_current_user_from_cookie(db=db, session=session)


@router.post("/create", response_model=Customer)
async def create_customer(
    customer: CustomerCreate,
    _current_user: Annotated[User, Depends(_get_current_user)],
    db: Session = Depends(get_db),  # noqa: B008
) -> Customer:
    """Create a new customer. Requires authentication."""
    try:
        new_customer = db_create_customer(db=db, customer=customer)
        return new_customer
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error creating customer",
        ) from e
