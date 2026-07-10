"""customer.py - FastAPI router for customer-related endpoints."""

import http
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.db.database import get_db
from src.api.v1.auth.auth import get_current_user_from_cookie
from src.api.v1.user.models import User

from .models import Customer, CustomerCreate, db_create_customer

router = APIRouter(prefix="/customer", tags=["Customer"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user_from_cookie)]


@router.post("/create", response_model=Customer, status_code=http.HTTPStatus.CREATED)
async def create_customer(
    customer: CustomerCreate,
    _current_user: CurrentUser,
    db: DbSession,
) -> Customer:
    """Create a new customer. Requires authentication."""
    try:
        return db_create_customer(db=db, customer=customer)
    except IntegrityError as e:
        raise HTTPException(
            status_code=http.HTTPStatus.CONFLICT,
            detail="A customer with this email already exists.",
        ) from e
