"""API endpoints for managing cases.

This module provides routes for retrieving case information,
including functions to get cases by ID and generate fake case data.
"""

import http
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query  # type: ignore
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid_extensions import uuid7

from src.api.db.database import get_db as get_db_session
from src.api.v1.auth.auth import get_current_user_from_cookie
from src.api.v1.auth.fga import delete_tuple, filter_by_permission, require_permission, write_tuple, write_tuple_safe
from src.api.v1.user.models import User, UserDB

from .models import (
    Case,
    CaseActivity,
    CaseCreate,
    CaseDB,
    CaseUpdate,
    DocumentInfo,
    db_create_case,
    db_delete_case,
    db_get_case,
    db_get_case_activities,
    db_log_activity,
    db_search_cases_by_user,
    db_update_case,
)
from .storage import delete_case_document, delete_case_documents, list_case_documents, stream_case_document

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
    q: Optional[str] = Query(default=None, description='Search customer or responsible person (case-insensitive)'),
    status: Optional[str] = Query(default=None, description='Filter by exact status value'),
    archived: Optional[bool] = Query(default=None, description='Filter by archived state'),
) -> list[Case]:
    """Get cases for the current user, with optional DB-level filtering, then FGA viewer check."""
    cases = db_search_cases_by_user(db=db, user_id=current_user.username, q=q, status=status, archived=archived)
    return await filter_by_permission(cases, current_user.username)


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
    result = db_create_case(db=db, case=case, user_id=current_user.username, case_id=case_id)
    await write_tuple(current_user.username, 'creator', 'case', case_id)
    await write_tuple(case.company_id, 'company', 'case', case_id, subject_type='company')
    if case.responsible_user_id:
        await write_tuple(case.responsible_user_id, 'assignee', 'case', case_id)
    # Ensure the creator is a member of the company (for viewer access to all company cases)
    await write_tuple_safe(current_user.username, 'member', 'company', case.company_id)
    # If the creator has a parent admin, establish their FGA admin relation to the company
    # so they can delete cases created by their sub-users.
    if current_user.parent_id:
        parent = db.query(UserDB).filter(UserDB.username == current_user.parent_id).first()
        if parent and parent.is_admin:
            await write_tuple_safe(parent.username, 'admin', 'company', case.company_id)
    db_log_activity(db, case_id, current_user.username, 'case_created')
    return result


@router.delete(
    '/{case_id}',
    status_code=http.HTTPStatus.NO_CONTENT,
    summary='Delete a case',
)
async def delete_case(
    case_id: str,
    db: DbSession,
    _auth: Annotated[User, Depends(require_permission('deleter'))],
) -> None:
    """Delete a case and clean up its OpenFGA tuples."""
    row = _get_case_db_or_404(db, case_id)
    creator_id = row.user_id
    company_id = row.company_id
    assignee_id = row.responsible_user_id
    db_delete_case(db=db, case_id=case_id)
    delete_case_documents(case_id)
    await delete_tuple(creator_id, 'creator', 'case', case_id)
    await delete_tuple(company_id, 'company', 'case', case_id, subject_type='company')
    if assignee_id:
        await delete_tuple(assignee_id, 'assignee', 'case', case_id)


def _validate_update_fields(db: Session, update_data: dict, old: CaseDB, current_user: User) -> None:
    """Validate customer transfer and responsible person change before applying an update."""
    if 'customer' in update_data and update_data['customer'] != old.customer:
        existing = db.query(CaseDB.customer).filter(
            CaseDB.company_id == old.company_id,
            CaseDB.customer == update_data['customer'],
        ).first()
        if not existing:
            raise HTTPException(
                status_code=http.HTTPStatus.BAD_REQUEST,
                detail=f'Customer "{update_data["customer"]}" does not exist for this company.',
            )

    if 'responsible_person' in update_data:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=http.HTTPStatus.FORBIDDEN,
                detail='Only admins can change the responsible person.',
            )
        name = update_data['responsible_person']
        case_creator = db.query(UserDB).filter(UserDB.username == old.user_id).first()
        if case_creator:
            team_parent = case_creator.username if case_creator.is_admin else case_creator.parent_id
        else:
            team_parent = None
        user_match = db.query(UserDB).filter(
            (UserDB.parent_id == team_parent) | (UserDB.username == team_parent),
            (UserDB.full_name == name) | (UserDB.username == name),
        ).first() if team_parent else None
        if not user_match:
            raise HTTPException(
                status_code=http.HTTPStatus.BAD_REQUEST,
                detail=f'User "{name}" not found in this company.',
            )


@router.patch(
    '/{case_id}',
    response_model=Case,
    status_code=http.HTTPStatus.OK,
    summary='Update a case',
)
async def update_case(
    case_id: str,
    case_update: CaseUpdate,
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission('editor'))],
) -> Case:
    """Apply a partial update to a case and log field changes."""
    update_data = case_update.model_dump(exclude_unset=True)
    old = _get_case_db_or_404(db, case_id)
    _validate_update_fields(db, update_data, old, current_user)

    # Capture values before db_update_case modifies the same ORM object in-place
    old_customer = old.customer
    old_status = old.status
    old_responsible = old.responsible_person
    old_responsible_user_id = old.responsible_user_id
    result = db_update_case(db=db, case_id=case_id, case_update=case_update)
    if not result:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND, detail='Case not found.')
    if 'customer' in update_data and update_data['customer'] != old_customer:
        detail = f'{old_customer} → {update_data["customer"]}'
        db_log_activity(db, case_id, current_user.username, 'customer_changed', detail)
    if 'status' in update_data and update_data['status'] != old_status:
        db_log_activity(db, case_id, current_user.username, 'status_changed', f'{old_status} → {update_data["status"]}')
    if 'responsible_person' in update_data and update_data['responsible_person'] != old_responsible:
        detail = f'{old_responsible} → {update_data["responsible_person"]}'
        db_log_activity(db, case_id, current_user.username, 'responsible_changed', detail)
        new_responsible_user_id = db.query(CaseDB.responsible_user_id).filter(CaseDB.id == case_id).scalar()
        if old_responsible_user_id:
            await delete_tuple(old_responsible_user_id, 'assignee', 'case', case_id)
        if new_responsible_user_id:
            await write_tuple(new_responsible_user_id, 'assignee', 'case', case_id)
    if 'archived' in update_data:
        action = 'case_archived' if update_data['archived'] else 'case_unarchived'
        db_log_activity(db, case_id, current_user.username, action)
    return result


@router.get(
    '/{case_id}/activity',
    response_model=list[CaseActivity],
    status_code=http.HTTPStatus.OK,
    summary='Get activity log for a case',
)
async def get_case_activity(
    case_id: str,
    db: DbSession,
    _auth: Annotated[User, Depends(require_permission('viewer'))],
) -> list[CaseActivity]:
    """Return all activity entries for a case, oldest first."""
    _get_case_db_or_404(db, case_id)
    return db_get_case_activities(db, case_id)


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


@router.delete(
    '/{case_id}/documents/{filename}',
    status_code=http.HTTPStatus.NO_CONTENT,
    summary='Delete a document attached to a case',
)
async def delete_case_document_endpoint(
    case_id: str,
    filename: str,
    db: DbSession,
    current_user: Annotated[User, Depends(require_permission('editor'))],
) -> None:
    """Delete a single document from MinIO and log the action."""
    _get_case_db_or_404(db, case_id)
    try:
        delete_case_document(case_id, filename)
    except ValueError as e:
        raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail=str(e)) from e
    db_log_activity(db, case_id, current_user.username, 'document_deleted', filename)


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
    try:
        stream, content_type = stream_case_document(case_id, filename)
    except ValueError as e:
        raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail=str(e)) from e
    from urllib.parse import quote
    safe_filename = quote(filename, safe='')
    return StreamingResponse(
        stream,
        media_type=content_type,
        headers={'Content-Disposition': f"attachment; filename*=UTF-8''{safe_filename}"},
    )
