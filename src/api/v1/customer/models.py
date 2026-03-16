"""Customer model for API v1."""

from typing import Optional

import pydantic
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session
from uuid_extensions import uuid7

from src.api.db.database import Base


# SQLAlchemy ORM model for database operations
class CustomerDB(Base):
    """SQLAlchemy ORM model for Customer table."""

    __tablename__ = "customers"

    id = Column(UUID(as_uuid=False), primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)


# Pydantic models for API validation
class Customer(pydantic.BaseModel):  # noqa: D101
    id: Optional[str] = pydantic.Field(
        default=None,
        description="Auto-generated UUID by PostgreSQL",
    )
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None

    class Config:
        """Pydantic config."""

        from_attributes = True  # Allows converting SQLAlchemy model to Pydantic model


class CustomerCreate(pydantic.BaseModel):  # noqa: D101, RUF100
    """Model for creating a new customer."""

    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None


def db_create_customer(db: Session, customer: CustomerCreate) -> Customer:
    """Create a new customer instance.

    Args:
        db (Session): The database session.
        customer (CustomerCreate): The customer data to create.

    Returns:
        Customer: A new Customer instance.

    """
    try:
        # Create a new CustomerDB instance with UUID
        db_customer = CustomerDB(
            id=str(uuid7()),
            name=customer.name,
            email=customer.email,
            phone=customer.phone,
            address=customer.address,
        )
        db.add(db_customer)
        db.commit()
        db.refresh(db_customer)

        # Convert to Pydantic model and return
        return Customer.model_validate(db_customer)
    except Exception:
        db.rollback()
        raise
