"""API endpoints for managing cases.

This module provides routes for retrieving case information,
including functions to get cases by ID and generate fake case data.
"""

import http
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException  # type: ignore
from sqlalchemy.orm import Session
from uuid_extensions import uuid7

from src.api.db.database import get_db as get_db_session
from src.api.v1.auth.auth import get_current_user_from_cookie
from src.api.v1.user.models import User

from .models import Case, CaseCreate, db_create_case, db_get_case, db_get_cases_by_user

router = APIRouter(prefix="/case", tags=["case"])

# Reusable annotated dependencies
DbSession = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user_from_cookie)]


@router.get(
    "/",
    response_model=list[Case],
    status_code=http.HTTPStatus.OK,
    summary="Get all cases for the current user",
)
async def get_my_cases(
    db: DbSession,
    current_user: CurrentUser,
) -> list[Case]:
    """Get all cases belonging to the current authenticated user."""
    return db_get_cases_by_user(db=db, user_id=current_user.id)


@router.get(
    "/{case_id}",
    response_model=Case,
    status_code=http.HTTPStatus.OK,
    summary="Get a case by ID",
)
async def get_case(case_id: str, db: DbSession) -> Case:
    """Retrieve a case by its ID."""
    if not case_id:
        raise HTTPException(
            status_code=http.HTTPStatus.BAD_REQUEST,
            detail="Case ID is required.",
        )
    case = db_get_case(db=db, case_id=case_id)
    if not case:
        raise HTTPException(
            status_code=http.HTTPStatus.NOT_FOUND,
            detail="Case not found.",
        )
    return case


@router.post(
    "/create",
    response_model=Case,
    status_code=http.HTTPStatus.CREATED,
    summary="Create a new case",
)
async def create_case(
    case: CaseCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> Case:
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
    # Generate a unique case ID
    case_id = str(uuid7())
    return db_create_case(db=db, case=case, user_id=current_user.id, case_id=case_id)
