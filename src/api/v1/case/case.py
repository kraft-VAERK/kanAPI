"""API endpoints for managing cases.

This module provides routes for retrieving case information,
including functions to get cases by ID and generate fake case data.
"""

import http
import random

from fastapi import APIRouter, Depends, HTTPException  # type: ignore
from sqlalchemy.orm import Session

from src.api.db.database import get_db as get_db_session

from ...db.postgres import PostgresDB
from .models import Case, db_create_case, db_get_case

router = APIRouter(prefix="/case", tags=["case"])

# Create a reusable dependency
db_dependency = Depends(get_db_session)


# Legacy database dependency - keeping for reference
def get_db() -> None:  # type: ignore
    """Get database session."""
    db = PostgresDB()
    session = db.connect()
    try:
        yield session
    finally:
        session.close()


@router.get(
    "/{case_id}",
    response_model=Case,
    status_code=http.HTTPStatus.OK,
    summary="Get a case by ID",
)
async def get_case(case_id: str, db: Session = db_dependency) -> Case:
    """Retrieve a case by its ID."""
    if not case_id:
        raise HTTPException(
            status_code=http.HTTPStatus.BAD_REQUEST,
            detail="Case ID is required.",
        )
    return db_get_case(db=db, case_id=case_id)


@router.post(
    "/create",
    response_model=Case,
    status_code=http.HTTPStatus.CREATED,
    summary="Create a new case",
)
async def create_case(case: Case, db: Session = db_dependency) -> Case:
    """Create a new case."""
    if not case.responsible_person:
        raise HTTPException(
            status_code=http.HTTPStatus.BAD_REQUEST,
            detail="Responsible person is required.",
        )
    if not case.status:
        raise HTTPException(
            status_code=http.HTTPStatus.BAD_REQUEST,
            detail="Status is required.",
        )
    if not case.customer:
        raise HTTPException(
            status_code=http.HTTPStatus.BAD_REQUEST,
            detail="Customer is required.",
        )
    # Generate a random case ID
    case.id = str(random.randint(1000, 9999))
    return db_create_case(db=db, case=case)
