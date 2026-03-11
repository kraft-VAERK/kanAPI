"""Tests for user CRUD functions and delete/get-by-id endpoint guards.

Hierarchy used across all tests:
  super_admin  (is_admin=True,  parent_id=None)
  company_admin (is_admin=True,  parent_id=super_admin.id)
  regular_user  (is_admin=False, parent_id=company_admin.id)
"""

import http
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from src.api.v1.case.models import CaseDB
from src.api.v1.user.models import User, UserDB, UserUpdate, db_update_user
from src.api.v1.user.user import delete_user_by_id, get_user

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_user(db, *, username, is_admin, parent_id=None):  # noqa ANN001
    """Insert a UserDB row and return the ORM instance."""
    uid = str(uuid.uuid4())
    row = UserDB(
        id=uid,
        username=username,
        email=f"{username}@test.dev",
        full_name=username.title(),
        password="hashed",
        is_active=True,
        is_admin=is_admin,
        parent_id=parent_id,
    )
    db.add(row)
    db.flush()
    return row


def _as_user(row):  # noqa ANN001
    """Convert a UserDB ORM row to the Pydantic User model used by auth."""
    return User(
        id=row.id,
        username=row.username,
        email=row.email,
        full_name=row.full_name,
        is_admin=row.is_admin,
        parent_id=row.parent_id,
    )


@pytest.fixture
def scenario(db):  # noqa ANN001
    """Insert super_admin, company_admin, and regular_user; return named refs."""
    super_admin = _make_user(db, username="super_admin", is_admin=True)
    company_admin = _make_user(db, username="company_admin", is_admin=True, parent_id=super_admin.id)
    regular_user = _make_user(db, username="regular_user", is_admin=False, parent_id=company_admin.id)
    return {
        "db": db,
        "super_admin": super_admin,
        "company_admin": company_admin,
        "regular_user": regular_user,
    }


# ─── db_update_user ───────────────────────────────────────────────────────────


def test_db_update_user_changes_username(scenario):  # noqa ANN001
    """db_update_user applies partial updates to an existing user."""
    s = scenario
    target = s["regular_user"]
    result = db_update_user(s["db"], target.id, UserUpdate(username="new_username"))
    assert result is not None
    assert result.username == "new_username"
    # unchanged fields stay the same
    assert result.email == target.email


def test_db_update_user_returns_none_for_missing_id(scenario):  # noqa ANN001
    """db_update_user returns None when the user ID does not exist."""
    result = db_update_user(scenario["db"], str(uuid.uuid4()), UserUpdate(username="ghost"))
    assert result is None


def test_db_update_user_hashes_password(scenario):  # noqa ANN001
    """db_update_user stores a SHA-256 hash, not the plaintext password."""
    import hashlib

    s = scenario
    target = s["regular_user"]
    db_update_user(s["db"], target.id, UserUpdate(password="newpass"))
    row = s["db"].query(UserDB).filter(UserDB.id == target.id).first()
    assert row.password == hashlib.sha256(b"newpass").hexdigest()


# ─── delete_user_by_id ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_user_non_admin_gets_403(scenario):  # noqa ANN001
    """A non-admin caller gets 403 when attempting to delete any user."""
    s = scenario
    caller = _as_user(s["regular_user"])
    with pytest.raises(HTTPException) as exc:
        await delete_user_by_id(s["super_admin"].id, caller, s["db"])
    assert exc.value.status_code == http.HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_delete_user_self_delete_gets_400(scenario):  # noqa ANN001
    """An admin gets 400 when trying to delete their own account."""
    s = scenario
    caller = _as_user(s["super_admin"])
    with pytest.raises(HTTPException) as exc:
        await delete_user_by_id(s["super_admin"].id, caller, s["db"])
    assert exc.value.status_code == http.HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
async def test_delete_user_missing_user_gets_404(scenario):  # noqa ANN001
    """An admin gets 404 when the target user ID does not exist."""
    s = scenario
    caller = _as_user(s["super_admin"])
    with pytest.raises(HTTPException) as exc:
        await delete_user_by_id(str(uuid.uuid4()), caller, s["db"])
    assert exc.value.status_code == http.HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_delete_user_success(scenario):  # noqa ANN001
    """An admin can delete another user; the row is removed from the DB."""
    s = scenario
    caller = _as_user(s["super_admin"])
    target_id = s["regular_user"].id

    await delete_user_by_id(target_id, caller, s["db"])

    row = s["db"].query(UserDB).filter(UserDB.id == target_id).first()
    assert row is None


@pytest.mark.asyncio
async def test_company_admin_can_delete_user(scenario):  # noqa ANN001
    """A company admin (is_admin=True) can also delete other users."""
    s = scenario
    caller = _as_user(s["company_admin"])
    target_id = s["regular_user"].id

    await delete_user_by_id(target_id, caller, s["db"])

    row = s["db"].query(UserDB).filter(UserDB.id == target_id).first()
    assert row is None


@pytest.mark.asyncio
async def test_delete_user_with_cases_gets_409(scenario, db):  # noqa ANN001
    """Deleting a user who owns cases returns 409 Conflict."""
    s = scenario
    caller = _as_user(s["super_admin"])
    target = s["regular_user"]

    # Give the target user a case
    company_id = str(uuid.uuid4())
    from src.api.v1.company.models import CompanyDB

    db.add(CompanyDB(id=company_id, name="Test Co", created_at=datetime.now(timezone.utc)))
    db.flush()
    db.add(
        CaseDB(
            id=str(uuid.uuid4()),
            responsible_person="Test",
            status="open",
            customer="Acme",
            company_id=company_id,
            created_at=datetime.now(timezone.utc),
            user_id=target.id,
        ),
    )
    db.flush()

    with pytest.raises(HTTPException) as exc:
        await delete_user_by_id(target.id, caller, db)
    assert exc.value.status_code == http.HTTPStatus.CONFLICT


# ─── get_user ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_user_non_admin_gets_403(scenario):  # noqa ANN001
    """A non-admin caller gets 403 when trying to view a user profile."""
    s = scenario
    caller = _as_user(s["regular_user"])
    with pytest.raises(HTTPException) as exc:
        await get_user(s["super_admin"].id, caller, s["db"])
    assert exc.value.status_code == http.HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_get_user_missing_gets_404(scenario):  # noqa ANN001
    """An admin gets 404 when the requested user ID does not exist."""
    s = scenario
    caller = _as_user(s["super_admin"])
    with pytest.raises(HTTPException) as exc:
        await get_user(str(uuid.uuid4()), caller, s["db"])
    assert exc.value.status_code == http.HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_get_user_success(scenario):  # noqa ANN001
    """An admin can retrieve a user by ID and gets the correct data back."""
    s = scenario
    caller = _as_user(s["super_admin"])
    target = s["regular_user"]

    result = await get_user(target.id, caller, s["db"])

    assert result.id == target.id
    assert result.username == target.username
    assert result.email == target.email
