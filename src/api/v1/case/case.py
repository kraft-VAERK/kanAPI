"""API endpoints for managing cases.

This module provides routes for retrieving case information,
including functions to get cases by ID and generate fake case data.
"""

import http
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException  # type: ignore
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid_extensions import uuid7

from src.api.db.database import get_db as get_db_session
from src.api.v1.auth.auth import get_current_user_from_cookie
from src.api.v1.user.models import User, UserDB

from .models import Case, CaseCreate, CaseDB, DocumentInfo, db_create_case, db_get_case, db_get_cases_by_user
from .storage import list_case_documents, stream_case_document

router = APIRouter(prefix="/case", tags=["case"])

# Reusable annotated dependencies
DbSession = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user_from_cookie)]


def _authorize_case_access(db: Session, case_db: CaseDB, current_user: User) -> None:
    """Raise 403 if current_user is not allowed to access this case.

    Access rules:
    - Super admin (is_admin=True, parent_id=None): always allowed.
    - Company admin (is_admin=True, parent_id set): allowed if the case owner
      belongs to their company (owner.parent_id == current_user.id).
    - Regular user: allowed if they own the case OR share the same company
      as the case owner (owner.parent_id == current_user.parent_id).
    """
    # Super admin — unrestricted
    if current_user.is_admin and current_user.parent_id is None:
        return

    owner = db.query(UserDB).filter(UserDB.id == case_db.user_id).first()
    if owner is None:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND, detail='Case not found.')

    # Company admin — must own the company the case owner belongs to
    if current_user.is_admin:
        if owner.parent_id == current_user.id:
            return
        raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail='Access denied.')

    # Regular user — same case owner or same company
    if owner.id == current_user.id:
        return
    if owner.parent_id is not None and owner.parent_id == current_user.parent_id:
        return

    raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail='Access denied.')


def _get_case_db_or_404(db: Session, case_id: str) -> CaseDB:
    """Return the raw CaseDB row or raise 404."""
    row = db.query(CaseDB).filter(CaseDB.id == case_id).first()
    if not row:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND, detail='Case not found.')
    return row


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
async def get_case(case_id: str, db: DbSession, current_user: CurrentUser) -> Case:
    """Retrieve a case by its ID."""
    case_db = _get_case_db_or_404(db, case_id)
    _authorize_case_access(db, case_db, current_user)
    return db_get_case(db=db, case_id=case_id)


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


@router.get(
    '/{case_id}/documents',
    response_model=list[DocumentInfo],
    status_code=http.HTTPStatus.OK,
    summary='List documents attached to a case',
)
async def get_case_documents(case_id: str, db: DbSession, current_user: CurrentUser) -> list[DocumentInfo]:
    """Return metadata for all documents stored in MinIO under cases/{case_id}/."""
    case_db = _get_case_db_or_404(db, case_id)
    _authorize_case_access(db, case_db, current_user)
    return list_case_documents(case_id)


@router.get(
    '/{case_id}/documents/{filename}',
    summary='Download a document attached to a case',
)
async def download_case_document(
    case_id: str,
    filename: str,
    db: DbSession,
    current_user: CurrentUser,
) -> StreamingResponse:
    """Stream a document from MinIO to the client."""
    case_db = _get_case_db_or_404(db, case_id)
    _authorize_case_access(db, case_db, current_user)
    stream, content_type = stream_case_document(case_id, filename)
    return StreamingResponse(
        stream,
        media_type=content_type,
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )
