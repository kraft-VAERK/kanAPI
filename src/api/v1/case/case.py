"""API endpoints for managing cases.

This module provides routes for retrieving case information,
including functions to get cases by ID and generate fake case data.
"""

import http
import random
import time

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from ...db.postgres import PostgresDB
from .models import Case, db_create_case, db_get_case

router = APIRouter(prefix="/case", tags=["case"])

# Database dependency
def get_db() -> Session: # type: ignore
    """Get database session."""
    db = PostgresDB()
    session = db.get_session()
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
async def get_case(case_id: str) -> Case:
    """Retrieve a case by its ID."""
    if not case_id:
        raise HTTPException(
            status_code=http.HTTPStatus.BAD_REQUEST,
            detail="Case ID is required.",
        )
    return db_get_case(case_id=case_id)

@router.post(
    "/create",
    response_model=Case,
    status_code=http.HTTPStatus.CREATED,
    summary="Create a new case",
)
async def create_case(case: Case) -> Case:
    """Create a new case."""
    case.id = str(random.randint(1000, 9999))  # Generate a random case ID
    case.created_at = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    case.deleted = False  # Default to not deleted
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
    session = get_db()
    return db_create_case(session=session, case=case)
