"""user.py - FastAPI router for user-related endpoints."""

import http
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.db.database import get_db
from src.api.v1.auth.auth import get_current_user_from_cookie

from .models import (
    User,
    UserChangelog,
    UserCreate,
    UserDB,
    UserPublic,
    UserUpdate,
    db_create_user,
    db_get_user_changelog,
    db_log_user_changes,
    db_update_user,
)

router = APIRouter(prefix="/user", tags=["User"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user_from_cookie)]


@router.post("/create", response_model=UserPublic, status_code=http.HTTPStatus.CREATED)
async def create_user(
    user: UserCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> User:
    """Create a new user. Requires admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail='Only admins can create users.')

    if not current_user.is_super_admin:
        # Company admins can only create sub-users under themselves
        if user.is_admin:
            raise HTTPException(
                status_code=http.HTTPStatus.FORBIDDEN,
                detail='Company admins cannot create admin users.',
            )
        user.parent_id = current_user.username

    try:
        return db_create_user(db=db, user_create=user)
    except IntegrityError as e:
        raise HTTPException(
            status_code=http.HTTPStatus.CONFLICT,
            detail="A user with this username or email already exists.",
        ) from e


@router.patch("/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> User:
    """Update a user's fields. Requires admin or super admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail='Only admins can update user information.')
    if not current_user.is_super_admin and current_user.username != user_id:
        target = db.query(UserDB).filter(UserDB.username == user_id).first()
        if not target or target.parent_id != current_user.username:
            raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail='You can only update users you manage.')

    before = db.query(UserDB).filter(UserDB.username == user_id).first()
    if not before:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND, detail='User not found.')

    updates = user_update.model_dump(exclude_none=True)
    db_log_user_changes(db=db, target_user=user_id, changed_by=current_user.username, before=before, updates=updates)

    result = db_update_user(db=db, username=user_id, user_update=user_update)
    if not result:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND, detail='User not found.')
    return result


@router.get("/all", response_model=List[UserPublic])
async def get_all_users(
    current_user: CurrentUser,
    db: DbSession,
) -> List[User]:
    """Get all users. Scoped by role: super admin sees all, others see own company."""
    if current_user.is_super_admin:
        users = db.query(UserDB).all()
    elif current_user.is_admin:
        # Company admin: see self + own sub-users
        users = db.query(UserDB).filter(
            (UserDB.username == current_user.username) | (UserDB.parent_id == current_user.username),
        ).all()
    else:
        # Regular user: see users in same company (same parent)
        users = db.query(UserDB).filter(
            (UserDB.username == current_user.parent_id) | (UserDB.parent_id == current_user.parent_id),
        ).all()
    return [User.model_validate(user) for user in users]


@router.delete("/{user_id}", status_code=http.HTTPStatus.NO_CONTENT)
async def delete_user_by_id(
    user_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Delete a user by ID. Requires admin. Cannot delete yourself."""
    if not current_user.is_admin:
        raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail="Only admins can delete users.")
    if current_user.username == user_id:
        raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail="You cannot delete your own account.")
    user_db = db.query(UserDB).filter(UserDB.username == user_id).first()
    if not user_db:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND, detail="User not found.")
    # Company admins can only delete their own sub-users
    if not current_user.is_super_admin and user_db.parent_id != current_user.username:
        raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail="You can only delete users you manage.")
    from src.api.v1.case.models import CaseDB  # local import to avoid circular dependency

    has_cases = (
        db.query(CaseDB)
        .filter((CaseDB.user_id == user_id) | (CaseDB.responsible_user_id == user_id))
        .first()
        is not None
    )
    if has_cases:
        raise HTTPException(
            status_code=http.HTTPStatus.CONFLICT,
            detail="Cannot delete user: they have associated cases. Delete or reassign their cases first.",
        )
    db.delete(user_db)
    db.commit()


@router.get("/{user_id}/cases", response_model=list)
async def get_user_cases(
    user_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> list:
    """Get all cases for a user. Admins can view managed users; users can view their own."""
    if current_user.username != user_id:
        if not current_user.is_admin:
            raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail="You can only view your own cases.")
        # Company admins can only view cases for their own sub-users
        if not current_user.is_super_admin:
            target = db.query(UserDB).filter(UserDB.username == user_id).first()
            if not target or target.parent_id != current_user.username:
                raise HTTPException(
                    status_code=http.HTTPStatus.FORBIDDEN,
                    detail="You can only view cases for users you manage.",
                )
    from src.api.v1.case.models import db_get_cases_by_responsible_user  # local import to avoid circular dependency

    return db_get_cases_by_responsible_user(db=db, user_id=user_id)


@router.get("/{user_id}/changelog", response_model=list[UserChangelog])
async def get_user_changelog(
    user_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> list[UserChangelog]:
    """Return field-level changelog for a user. Super admin only."""
    if not current_user.is_super_admin:
        raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail='Super admin access required.')
    return db_get_user_changelog(db=db, username=user_id)


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> User:
    """Get a user by ID. Requires admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail="Only admins can view user profiles.")
    user_db = db.query(UserDB).filter(UserDB.username == user_id).first()
    if not user_db:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND, detail="User not found.")
    return User.model_validate(user_db)
