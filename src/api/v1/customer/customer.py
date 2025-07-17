"""customer.py - FastAPI router for customer-related endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.db.database import get_db

from .models import Customer, CustomerCreate, db_create_customer

router = APIRouter(prefix="/customer", tags=["Customer"])


# @router.get("/{customer_id}", response_model=Customer)
# async def get_customer(customer_id: int) -> Customer:
#     """Retrieve a customer by ID."""
#     return Customer(id=customer_id, name=fake.name(), email=fake.email())


@router.post("/create", response_model=Customer)
async def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),  # noqa: B008
) -> Customer:
    """Create a new customer."""
    print(f"Creating customer: {customer}")

    try:
        new_customer = db_create_customer(db=db, customer=customer)
        return new_customer
    except Exception as e:
        print(f"Error creating customer: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error creating customer",
        ) from e
