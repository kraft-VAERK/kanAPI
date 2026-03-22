"""Company endpoints — accessible by super admin only."""

import http
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.db.database import get_db as get_db_session
from src.api.v1.auth.auth import get_current_user_from_cookie
from src.api.v1.auth.fga import filter_by_permission
from src.api.v1.case.models import Case, CaseDB, _apply_case_filters
from src.api.v1.company.models import (
    Company,
    CompanyCreate,
    CompanyDB,
    db_create_company,
    db_delete_company,
    db_get_client_companies,
    db_get_companies,
    db_get_company,
)
from src.api.v1.user.models import User, UserDB, UserPublic

router = APIRouter(prefix='/company', tags=['company'])

DbSession = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user_from_cookie)]


def _require_super_admin(user: User) -> None:
    if not user.is_admin or user.parent_id is not None:
        raise HTTPException(
            status_code=http.HTTPStatus.FORBIDDEN,
            detail='Super admin access required.',
        )


def _require_company_admin(user: User) -> None:
    if not user.is_admin or user.parent_id is None:
        raise HTTPException(
            status_code=http.HTTPStatus.FORBIDDEN,
            detail='Company admin access required.',
        )


@router.get('/', response_model=list[Company], status_code=http.HTTPStatus.OK)
async def get_companies(_current_user: CurrentUser, db: DbSession) -> list[Company]:
    """Return all companies. Any authenticated user can list companies (needed for case creation)."""
    return db_get_companies(db)


@router.post('/', response_model=Company, status_code=http.HTTPStatus.CREATED)
async def create_company(
    company: CompanyCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Company:
    """Create a new company. Super admin only."""
    _require_super_admin(current_user)
    return db_create_company(db=db, company_create=company)


@router.delete('/{company_id}', status_code=http.HTTPStatus.NO_CONTENT)
async def delete_company(company_id: str, current_user: CurrentUser, db: DbSession) -> None:
    """Delete a company by ID. Super admin only."""
    _require_super_admin(current_user)
    if not db_delete_company(db=db, company_id=company_id):
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND, detail='Company not found.')


@router.get('/my-users', response_model=list[UserPublic], status_code=http.HTTPStatus.OK)
async def get_my_users(current_user: CurrentUser, db: DbSession) -> list[User]:
    """Return all sub-users belonging to the current company admin."""
    _require_company_admin(current_user)
    rows = db.query(UserDB).filter(UserDB.parent_id == current_user.username).all()
    return [User.model_validate(r) for r in rows]


@router.get('/mine', response_model=list[Company], status_code=http.HTTPStatus.OK)
async def get_my_companies(current_user: CurrentUser, db: DbSession) -> list[Company]:
    """Return the distinct companies associated with the current company admin.

    Derived from the company_ids on cases owned by their sub-users.
    """
    _require_company_admin(current_user)
    sub_user_ids = [u.username for u in db.query(UserDB).filter(UserDB.parent_id == current_user.username).all()]
    if not sub_user_ids:
        return []
    company_ids = [
        r[0] for r in db.query(CaseDB.company_id).filter(CaseDB.user_id.in_(sub_user_ids)).distinct().all()
    ]
    if not company_ids:
        return []
    rows = db.query(CompanyDB).filter(CompanyDB.id.in_(company_ids)).all()
    return [Company.model_validate(r) for r in rows]


@router.get('/my-cases', response_model=list[Case], status_code=http.HTTPStatus.OK)
async def get_my_company_cases(
    current_user: CurrentUser,
    db: DbSession,
    q: Optional[str] = Query(default=None, description='Search customer or responsible person (case-insensitive)'),
    status: Optional[str] = Query(default=None, description='Filter by exact status value'),
    archived: Optional[bool] = Query(default=None, description='Filter by archived state'),
) -> list[Case]:
    """Return all cases across sub-users of the current company admin."""
    _require_company_admin(current_user)
    sub_user_ids = [
        u.username for u in db.query(UserDB).filter(UserDB.parent_id == current_user.username).all()
    ]
    all_user_ids = [current_user.username, *sub_user_ids]
    query = db.query(CaseDB).filter(CaseDB.user_id.in_(all_user_ids))
    query = _apply_case_filters(query, q=q, status=status, archived=archived)
    db_cases = query.all()
    return [
        Case(
            id=c.id,
            responsible_person=c.responsible_person,
            status=c.status,
            customer=c.customer,
            company_id=c.company_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in db_cases
    ]


@router.get('/{company_id}', response_model=Company, status_code=http.HTTPStatus.OK)
async def get_company(company_id: str, _current_user: CurrentUser, db: DbSession) -> Company:
    """Return a single company by ID. Any authenticated user can view."""
    company = db_get_company(db=db, company_id=company_id)
    if not company:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND, detail='Company not found.')
    return company


@router.get('/{company_id}/clients', response_model=list[Company], status_code=http.HTTPStatus.OK)
async def get_client_companies(company_id: str, current_user: CurrentUser, db: DbSession) -> list[Company]:
    """Return all client companies owned by this company."""
    _require_super_admin(current_user)
    return db_get_client_companies(db=db, owner_id=company_id)


@router.get('/{company_id}/users', response_model=list[UserPublic], status_code=http.HTTPStatus.OK)
async def get_company_users(company_id: str, current_user: CurrentUser, db: DbSession) -> list[User]:
    """Return all sub-users belonging to a company (user-based admin accounts)."""
    _require_super_admin(current_user)
    client_ids = [r.id for r in db.query(CompanyDB).filter(CompanyDB.owner_id == company_id).all()]
    all_ids = [company_id, *client_ids]
    user_ids = db.query(CaseDB.user_id).filter(CaseDB.company_id.in_(all_ids)).distinct().subquery()
    rows = db.query(UserDB).filter(UserDB.username.in_(user_ids)).all()
    return [User.model_validate(r) for r in rows]


@router.get('/{company_id}/cases', response_model=list[Case], status_code=http.HTTPStatus.OK)
async def get_company_cases(
    company_id: str,
    current_user: CurrentUser,
    db: DbSession,
    q: Optional[str] = Query(default=None, description='Search customer or responsible person (case-insensitive)'),
    status: Optional[str] = Query(default=None, description='Filter by exact status value'),
    archived: Optional[bool] = Query(default=None, description='Filter by archived state'),
) -> list[Case]:
    """Return cases for this company. Super admins see client-company cases too; others are FGA-filtered."""
    is_super = current_user.is_admin and not current_user.parent_id
    if is_super:
        client_ids = [r.id for r in db.query(CompanyDB).filter(CompanyDB.owner_id == company_id).all()]
        all_ids = [company_id, *client_ids]
        query = db.query(CaseDB).filter(CaseDB.company_id.in_(all_ids))
    else:
        query = db.query(CaseDB).filter(CaseDB.company_id == company_id)
    query = _apply_case_filters(query, q=q, status=status, archived=archived)
    db_cases = query.all()
    cases = [
        Case(
            id=c.id,
            responsible_person=c.responsible_person,
            responsible_user_id=c.responsible_user_id,
            status=c.status,
            customer=c.customer,
            company_id=c.company_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in db_cases
    ]
    if not is_super:
        cases = await filter_by_permission(cases, current_user.username)
    return cases
