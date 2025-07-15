"""Module defines the data models for the case management system."""

from typing import List, Optional

import psycopg2  # noqa: F401
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


class CaseCreate(BaseModel):
    """Model for creating a new case."""

    responsible_person: str
    status: str
    customer: str


class CaseUpdate(BaseModel):
    """Model for updating an existing case."""

    responsible_person: Optional[str] = None
    status: Optional[str] = None
    customer: Optional[str] = None


class CaseDelete(BaseModel):
    """Model for deleting a case."""

    id: str
    deleted: bool = True


class Case(BaseModel):
    """Represents a case in the system.

    Attributes
    ----------
    id : str
        Unique identifier for the case.
    deleted : bool
        Flag indicating if the case has been deleted.
    responsible_person : str
        Name of the person responsible for the case.
    status : str
        Current status of the case.
    customer : str
        Name of the customer associated with the case.
    created_at : str
        Timestamp when the case was created.
    title : str

    """

    id: str
    deleted: bool = False
    responsible_person: str
    status: str
    customer: str
    created_at: str
    title: Optional[str] = None


def db_create_case(db: Session, case: CaseCreate) -> Case:
    """Create a new case in the database.

    Args:
        db: Database session
        case: Case data to create

    Returns:
        The created case

    """
    try:
        db_case = Case(**case.model_dump())
        db.add(db_case)
        db.commit()
        db.refresh(db_case)
        return db_case
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e!s}") from e


def db_get_case(db: Session, case_id: int) -> Optional[Case]:
    """Get a case by ID.

    Args:
        db: Database session
        case_id: ID of the case to retrieve

    Returns:
        The case if found, None otherwise

    """
    return db.query(Case).filter(Case.id == case_id).first()


def db_get_cases(db: Session, skip: int = 0, limit: int = 100) -> List[Case]:
    """Get all cases with pagination.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of cases

    """
    return db.query(Case).offset(skip).limit(limit).all()


def db_update_case(
    db: Session,
    case_id: int,
    case_update: CaseUpdate,
) -> Optional[Case]:
    """Update a case.

    Args:
        db: Database session
        case_id: ID of the case to update
        case_update: Updated case data

    Returns:
        The updated case if found, None otherwise

    """
    try:
        db_case = db_get_case(db, case_id)
        if db_case:
            update_data = case_update.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_case, key, value)
            db.commit()
            db.refresh(db_case)
        return db_case
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e!s}") from e


def db_delete_case(db: Session, case_id: int) -> bool:
    """Delete a case.

    Args:
        db: Database session
        case_id: ID of the case to delete

    Returns:
        True if the case was deleted, False otherwise

    """
    try:
        db_case = db_get_case(db, case_id)
        if db_case:
            db.delete(db_case)
            db.commit()
            return True
        return False
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e!s}") from e
