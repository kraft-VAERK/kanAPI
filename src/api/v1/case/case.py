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
from src.api.v1.auth.fga import filter_by_permission, require_permission, write_tuple
from src.api.v1.user.models import User

from .models import Case, CaseCreate, CaseDB, DocumentInfo, db_create_case, db_get_case, db_get_cases_by_user
from .storage import list_case_documents, stream_case_document

router = APIRouter(prefix="/case", tags=["case"])

# Reusable annotated dependencies
DbSession = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user_from_cookie)]


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
    """Get all cases belonging to the current authenticated user, filtered by OpenFGA viewer permission."""
    cases = db_get_cases_by_user(db=db, user_id=current_user.id)
    return await filter_by_permission(cases, current_user.id)


@router.get(
    "/{case_id}",
    response_model=Case,
    status_code=http.HTTPStatus.OK,
    summary="Get a case by ID",
)
async def get_case(
    case_id: str,
    db: DbSession,
    _auth: Annotated[User, Depends(require_permission('viewer'))],
) -> Case:
    """Retrieve a case by its ID."""
    result = db_get_case(db=db, case_id=case_id)
    if not result:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND, detail='Case not found.')
    return result


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
    """Create a new case and register the creator relationship in OpenFGA."""
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
    case_id = str(uuid7())
    result = db_create_case(db=db, case=case, user_id=current_user.id, case_id=case_id)
    await write_tuple(current_user.id, 'creator', 'case', case_id)
    return result


@router.get(
    '/{case_id}/documents',
    response_model=list[DocumentInfo],
    status_code=http.HTTPStatus.OK,
    summary='List documents attached to a case',
)
async def get_case_documents(
    case_id: str,
    db: DbSession,
    _auth: Annotated[User, Depends(require_permission('viewer'))],
) -> list[DocumentInfo]:
    """Return metadata for all documents stored in MinIO under cases/{case_id}/."""
    _get_case_db_or_404(db, case_id)
    return list_case_documents(case_id)


@router.get(
    '/{case_id}/documents/{filename}',
    summary='Download a document attached to a case',
)
async def download_case_document(
    case_id: str,
    filename: str,
    db: DbSession,
    _auth: Annotated[User, Depends(require_permission('viewer'))],
) -> StreamingResponse:
    """Stream a document from MinIO to the client."""
    _get_case_db_or_404(db, case_id)
    stream, content_type = stream_case_document(case_id, filename)
    return StreamingResponse(
        stream,
        media_type=content_type,
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )
