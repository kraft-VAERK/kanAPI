"""Company model for API v1."""

import http
from datetime import datetime, timezone
from typing import Optional

import pydantic
from fastapi import HTTPException
from pydantic import ConfigDict
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from uuid_extensions import uuid7

from src.api.db.database import Base


class CompanyDB(Base):
    """SQLAlchemy ORM model for Company table."""

    __tablename__ = 'companies'

    id = Column(UUID(as_uuid=False), primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    owner_id = Column(UUID(as_uuid=False), ForeignKey('companies.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)


class Company(pydantic.BaseModel):
    """Pydantic model for Company."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    owner_id: Optional[str] = None
    created_at: datetime


class CompanyCreate(pydantic.BaseModel):
    """Pydantic model for creating a Company."""

    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    owner_id: Optional[str] = None


def db_create_company(db: Session, company_create: CompanyCreate) -> Company:
    """Create a new company in the database."""
    try:
        db_company = CompanyDB(
            id=str(uuid7()),
            name=company_create.name,
            email=company_create.email,
            phone=company_create.phone,
            address=company_create.address,
            owner_id=company_create.owner_id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(db_company)
        db.commit()
        db.refresh(db_company)
        return Company.model_validate(db_company)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Database error: {e!s}') from e


def db_get_companies(db: Session) -> list[Company]:
    """Return all companies."""
    rows = db.query(CompanyDB).all()
    return [Company.model_validate(r) for r in rows]


def db_get_company(db: Session, company_id: str) -> Optional[Company]:
    """Return a single company by ID."""
    row = db.query(CompanyDB).filter(CompanyDB.id == company_id).first()
    return Company.model_validate(row) if row else None


def db_get_client_companies(db: Session, owner_id: str) -> list[Company]:
    """Return all companies owned by the given company."""
    rows = db.query(CompanyDB).filter(CompanyDB.owner_id == owner_id).all()
    return [Company.model_validate(r) for r in rows]


def db_delete_company(db: Session, company_id: str) -> bool:
    """Delete a company by ID. Returns False if not found. Raises 409 if the company has cases."""
    from src.api.v1.case.models import CaseDB
    try:
        row = db.query(CompanyDB).filter(CompanyDB.id == company_id).first()
        if not row:
            return False
        case_count = db.query(CaseDB).filter(CaseDB.company_id == company_id).count()
        if case_count > 0:
            raise HTTPException(
                status_code=http.HTTPStatus.CONFLICT,
                detail=f'Cannot delete company: {case_count} case(s) are attached to it.',
            )
        db.delete(row)
        db.commit()
        return True
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Database error: {e!s}') from e
