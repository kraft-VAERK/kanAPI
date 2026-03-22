"""user.py - FastAPI router for user-related endpoints."""

from typing import Annotated, List

from fastapi import APIRouter, Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.db.database import get_db

from .models import User, UserCreate, UserDB, UserUpdate, db_create_user, db_delete_user, db_update_user

router = APIRouter(prefix="/user", tags=["User"])


async def get_user_from_cookie(
    db: Annotated[Session, Depends(get_db)],
    session: Annotated[str | None, Cookie()] = None,
) -> User:
    """Lazy wrapper to avoid circular import with auth module."""
    from src.api.v1.auth.auth import get_current_user_from_cookie

    return await get_current_user_from_cookie(db=db, session=session)


@router.post("/create", response_model=User)
async def create_user(
    user: UserCreate,
    current_user: Annotated[User, Depends(get_user_from_cookie)],
    db: Session = Depends(get_db),  # noqa: B008
) -> User:
    """Create a new user. Requires admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail='Only admins can create users.')

    is_super_admin = current_user.is_admin and not current_user.parent_id
    if not is_super_admin:
        # Company admins can only create sub-users under themselves
        if user.is_admin:
            raise HTTPException(status_code=403, detail='Company admins cannot create admin users.')
        user.parent_id = current_user.username

    try:
        new_user = db_create_user(db=db, user_create=user)
        return new_user
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error creating user",
        ) from e


@router.get("/delete", response_model=bool)
async def delete_user(
    user_delete: User,
    current_user: Annotated[User, Depends(get_user_from_cookie)],
    db: Session = Depends(get_db),  # noqa: B008
) -> bool:
    """Delete a user by user_id or email. Requires admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail='Only admins can delete users.')

    try:
        deleted = db_delete_user(db=db, user_delete=user_delete)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )
        return True
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error deleting user",
        ) from e


@router.patch("/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_user_from_cookie)],
    db: Session = Depends(get_db),  # noqa: B008
) -> User:
    """Update a user's fields. Requires admin or super admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail='Only admins can update user information.')
    is_super_admin = current_user.is_admin and not current_user.parent_id
    if not is_super_admin:
        is_self = current_user.username == user_id
        if not is_self:
            target = db.query(UserDB).filter(UserDB.username == user_id).first()
            if not target or target.parent_id != current_user.username:
                raise HTTPException(status_code=403, detail='You can only update users you manage.')
        user_update.username = None  # only super admin can change username
    result = db_update_user(db=db, username=user_id, user_update=user_update)
    if not result:
        raise HTTPException(status_code=404, detail='User not found.')
    return result


@router.get("/all", response_model=List[User])
async def get_all_users(
    _current_user: Annotated[User, Depends(get_user_from_cookie)],
    db: Session = Depends(get_db),  # noqa: B008
) -> List[User]:
    """Get all users. Scoped by role: super admin sees all, others see own company."""
    try:
        is_super_admin = _current_user.is_admin and not _current_user.parent_id
        if is_super_admin:
            users = db.query(UserDB).all()
        elif _current_user.is_admin:
            # Company admin: see self + own sub-users
            users = db.query(UserDB).filter(
                (UserDB.username == _current_user.username) | (UserDB.parent_id == _current_user.username),
            ).all()
        else:
            # Regular user: see users in same company (same parent)
            users = db.query(UserDB).filter(
                (UserDB.username == _current_user.parent_id) | (UserDB.parent_id == _current_user.parent_id),
            ).all()
        return [User.model_validate(user) for user in users]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error fetching users",
        ) from e


@router.delete("/{user_id}", status_code=204)
async def delete_user_by_id(
    user_id: str,
    current_user: Annotated[User, Depends(get_user_from_cookie)],
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    """Delete a user by ID. Requires admin. Cannot delete yourself."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can delete users.")
    if current_user.username == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")
    user_db = db.query(UserDB).filter(UserDB.username == user_id).first()
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found.")
    # Company admins can only delete their own sub-users
    is_super_admin = current_user.is_admin and not current_user.parent_id
    if not is_super_admin and user_db.parent_id != current_user.username:
        raise HTTPException(status_code=403, detail="You can only delete users you manage.")
    from src.api.v1.case.models import CaseDB  # local import to avoid circular dependency

    has_cases = db.query(CaseDB).filter(CaseDB.user_id == user_id).first() is not None
    if has_cases:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete user: \
                            they have associated cases. Delete their cases first.",
        )
    db.delete(user_db)
    db.commit()


@router.get("/{user_id}/cases", response_model=list)
async def get_user_cases(
    user_id: str,
    current_user: Annotated[User, Depends(get_user_from_cookie)],
    db: Session = Depends(get_db),  # noqa: B008
) -> list:
    """Get all cases for a user. Admins can view managed users; users can view their own."""
    if current_user.username != user_id:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="You can only view your own cases.")
        # Company admins can only view cases for their own sub-users
        is_super_admin = current_user.is_admin and not current_user.parent_id
        if not is_super_admin:
            target = db.query(UserDB).filter(UserDB.username == user_id).first()
            if not target or target.parent_id != current_user.username:
                raise HTTPException(status_code=403, detail="You can only view cases for users you manage.")
    from src.api.v1.case.models import db_get_cases_by_responsible_user  # local import to avoid circular dependency

    return db_get_cases_by_responsible_user(db=db, user_id=user_id)


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: str,
    current_user: Annotated[User, Depends(get_user_from_cookie)],
    db: Session = Depends(get_db),  # noqa: B008
) -> User:
    """Get a user by ID. Requires admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can view user profiles.")
    user_db = db.query(UserDB).filter(UserDB.username == user_id).first()
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found.")
    return User.model_validate(user_db)
