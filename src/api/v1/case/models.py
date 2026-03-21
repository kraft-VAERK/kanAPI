"""Module defines the data models for the case management system."""

from datetime import datetime, timezone
from typing import List, Optional

import pydantic
from fastapi import HTTPException
from pydantic import ConfigDict
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, or_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Query, Session

from src.api.db.database import Base


class CaseDB(Base):
    """SQLAlchemy ORM model for Case table."""

    __tablename__ = "cases"

    id = Column(UUID(as_uuid=False), primary_key=True, index=True)
    responsible_person = Column(String, nullable=False)
    responsible_user_id = Column(String, ForeignKey("users.username", onupdate='CASCADE'), nullable=True)
    status = Column(String, nullable=False)
    customer = Column(String, nullable=False)
    archived = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    user_id = Column(String, ForeignKey("users.username", onupdate='CASCADE'), nullable=False)
    company_id = Column(UUID(as_uuid=False), ForeignKey("companies.id"), nullable=False)


class DocumentInfo(pydantic.BaseModel):
    """Metadata for a document stored in MinIO."""

    name: str
    size: int
    last_modified: datetime


class CaseCreate(pydantic.BaseModel):
    """Model for creating a new case."""

    responsible_person: str
    responsible_user_id: Optional[str] = None
    status: str
    customer: str
    company_id: str


class CaseUpdate(pydantic.BaseModel):
    """Model for updating an existing case."""

    responsible_person: Optional[str] = None
    status: Optional[str] = None
    customer: Optional[str] = None
    archived: Optional[bool] = None
    updated_at: Optional[datetime] = None


class CaseDelete(pydantic.BaseModel):
    """Model for deleting a case."""

    id: str
    deleted: bool = True


class Case(pydantic.BaseModel):
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
    created_at : datetime
        Timestamp when the case was created.
    updated_at : datetime | None
        Timestamp when the case was last updated. Optional, as it may not be set initially.

    """

    id: str
    deleted: bool = False
    responsible_person: str
    responsible_user_id: Optional[str] = None
    status: str
    customer: str
    archived: bool = False
    company_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None


def db_create_case(db: Session, case: CaseCreate, user_id: str, case_id: str) -> Case:
    """Create a new case in the database.

    Args:
        db: Database session
        case: Case data to create
        user_id: ID of the user creating the case
        case_id: Unique ID for the case

    Returns:
        The created case

    """
    try:
        db_case = CaseDB(
            id=case_id,
            responsible_person=case.responsible_person,
            responsible_user_id=case.responsible_user_id,
            status=case.status,
            customer=case.customer,
            archived=False,
            company_id=case.company_id,
            created_at=datetime.now(timezone.utc),
            user_id=user_id,
        )
        db.add(db_case)
        db.commit()
        db.refresh(db_case)
        return Case(
            id=db_case.id,
            responsible_person=db_case.responsible_person,
            responsible_user_id=db_case.responsible_user_id,
            status=db_case.status,
            customer=db_case.customer,
            archived=db_case.archived,
            company_id=db_case.company_id,
            created_at=db_case.created_at,
            updated_at=db_case.updated_at,
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e!s}") from e


def db_get_case(db: Session, case_id: str) -> Optional[Case]:
    """Get a case by ID.

    Args:
        db: Database session
        case_id: ID of the case to retrieve

    Returns:
        The case if found, None otherwise

    """
    db_case = db.query(CaseDB).filter(CaseDB.id == case_id).first()
    if db_case:
        return Case(
            id=db_case.id,
            responsible_person=db_case.responsible_person,
            responsible_user_id=db_case.responsible_user_id,
            status=db_case.status,
            customer=db_case.customer,
            archived=db_case.archived,
            company_id=db_case.company_id,
            created_at=db_case.created_at,
            updated_at=db_case.updated_at,
        )
    return None


def db_get_cases(db: Session, skip: int = 0, limit: int = 100) -> List[Case]:
    """Get all cases with pagination.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of cases

    """
    db_cases = db.query(CaseDB).offset(skip).limit(limit).all()
    return [
        Case(
            id=c.id,
            responsible_person=c.responsible_person,
            responsible_user_id=c.responsible_user_id,
            status=c.status,
            customer=c.customer,
            archived=c.archived,
            company_id=c.company_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in db_cases
    ]


def db_update_case(
    db: Session,
    case_id: str,
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
        db_case = db.query(CaseDB).filter(CaseDB.id == case_id).first()
        if db_case:
            update_data = case_update.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_case, key, value)
            db.commit()
            db.refresh(db_case)
            return Case(
                id=db_case.id,
                responsible_person=db_case.responsible_person,
                status=db_case.status,
                customer=db_case.customer,
                archived=db_case.archived,
                company_id=db_case.company_id,
                created_at=db_case.created_at,
                updated_at=db_case.updated_at,
            )
        return None
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e!s}") from e


def db_get_cases_by_user(db: Session, user_id: str) -> List[Case]:
    """Get all cases belonging to a specific user.

    Args:
        db: Database session
        user_id: ID of the user whose cases to retrieve

    Returns:
        List of cases owned by the user

    """
    db_cases = db.query(CaseDB).filter(CaseDB.user_id == user_id).all()
    return [
        Case(
            id=c.id,
            responsible_person=c.responsible_person,
            responsible_user_id=c.responsible_user_id,
            status=c.status,
            customer=c.customer,
            archived=c.archived,
            company_id=c.company_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in db_cases
    ]


def _apply_case_filters(
    query: 'Query[CaseDB]',
    q: Optional[str] = None,
    status: Optional[str] = None,
    archived: Optional[bool] = None,
) -> 'Query[CaseDB]':
    """Apply optional search/filter criteria to a CaseDB query."""
    if q:
        query = query.filter(
            or_(
                CaseDB.customer.ilike(f'%{q}%'),
                CaseDB.responsible_person.ilike(f'%{q}%'),
            ),
        )
    if status is not None:
        query = query.filter(CaseDB.status == status)
    if archived is not None:
        query = query.filter(CaseDB.archived == archived)
    return query


def db_search_cases_by_user(
    db: Session,
    user_id: str,
    q: Optional[str] = None,
    status: Optional[str] = None,
    archived: Optional[bool] = None,
) -> List[Case]:
    """Search cases visible to a user with optional filters applied in the database.

    For users with a parent (sub-users), returns all cases in the same companies
    as their sibling users. For other users, returns only their own cases.
    FGA viewer permission is applied after this query.

    """
    from src.api.v1.user.models import UserDB

    user = db.query(UserDB).filter(UserDB.username == user_id).first()
    if user and user.parent_id:
        # Sub-user: get all cases from companies their team works in
        sibling_ids = db.query(UserDB.username).filter(UserDB.parent_id == user.parent_id).subquery()
        company_ids = (
            db.query(CaseDB.company_id).filter(CaseDB.user_id.in_(sibling_ids)).distinct().subquery()
        )
        query = db.query(CaseDB).filter(CaseDB.company_id.in_(company_ids))
    else:
        query = db.query(CaseDB).filter(CaseDB.user_id == user_id)
    query = _apply_case_filters(query, q=q, status=status, archived=archived)
    db_cases = query.all()
    return [
        Case(
            id=c.id,
            responsible_person=c.responsible_person,
            responsible_user_id=c.responsible_user_id,
            status=c.status,
            customer=c.customer,
            archived=c.archived,
            company_id=c.company_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in db_cases
    ]


def db_get_cases_by_responsible_user(db: Session, user_id: str) -> List[Case]:
    """Get all cases where the given user is the responsible person."""
    db_cases = db.query(CaseDB).filter(CaseDB.responsible_user_id == user_id).all()
    return [
        Case(
            id=c.id,
            responsible_person=c.responsible_person,
            responsible_user_id=c.responsible_user_id,
            status=c.status,
            customer=c.customer,
            archived=c.archived,
            company_id=c.company_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in db_cases
    ]


def db_delete_case(db: Session, case_id: str) -> bool:
    """Delete a case by ID. Returns True if deleted, False if not found."""
    try:
        db_case = db.query(CaseDB).filter(CaseDB.id == case_id).first()
        if not db_case:
            return False
        db.delete(db_case)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e!s}") from e


# ─── Case activity ─────────────────────────────────────────────────────────────


class CaseActivityDB(Base):
    """SQLAlchemy ORM model for case activity log."""

    __tablename__ = 'case_activities'

    id = Column(UUID(as_uuid=False), primary_key=True, index=True)
    case_id = Column(UUID(as_uuid=False), ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(String, ForeignKey('users.username', ondelete='SET NULL', onupdate='CASCADE'), nullable=True)
    action = Column(String, nullable=False)
    detail = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)


class CaseActivity(pydantic.BaseModel):
    """Pydantic model for a case activity entry."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    user_id: Optional[str] = None
    action: str
    detail: Optional[str] = None
    created_at: datetime


def db_log_activity(
    db: Session,
    case_id: str,
    user_id: Optional[str],
    action: str,
    detail: Optional[str] = None,
) -> None:
    """Append an activity entry for a case."""
    from uuid_extensions import uuid7
    try:
        db.add(CaseActivityDB(
            id=str(uuid7()),
            case_id=case_id,
            user_id=user_id,
            action=action,
            detail=detail,
            created_at=datetime.now(timezone.utc),
        ))
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Database error: {e!s}') from e


def db_get_case_activities(db: Session, case_id: str) -> list[CaseActivity]:
    """Return all activity entries for a case, oldest first."""
    rows = (
        db.query(CaseActivityDB)
        .filter(CaseActivityDB.case_id == case_id)
        .order_by(CaseActivityDB.created_at.asc())
        .all()
    )
    return [CaseActivity.model_validate(r) for r in rows]
