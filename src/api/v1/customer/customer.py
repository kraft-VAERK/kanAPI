"""customer.py - FastAPI router for customer-related endpoints."""

from faker import Faker
from fastapi import APIRouter

from src.api.v1.customer.models import Customer

router = APIRouter(prefix="/customer", tags=["Customer"])

fake = Faker()


@router.get("/{customer_id}", response_model=Customer)
async def get_customer(customer_id: int) -> Customer:
    """Retrieve a customer by ID.

    Args:
        customer_id (int): The ID of the customer to retrieve.

    Returns:
        Customer: The customer object with the specified ID.

    """
    return Customer(id=customer_id, name=fake.name(), email=fake.email())
