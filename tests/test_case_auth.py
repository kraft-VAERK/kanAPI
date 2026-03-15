"""Tests for case-level authorization via OpenFGA.

Hierarchy used across all tests:
  super_admin  (is_admin=True,  parent_id=None)
  ├── company_a  (is_admin=True,  parent_id=super_admin.username)
  │   ├── user_a1  (is_admin=False, parent_id=company_a.username)  ← owns case_a1
  │   └── user_a2  (is_admin=False, parent_id=company_a.username)  ← owns case_a2
  └── company_b  (is_admin=True,  parent_id=super_admin.username)
      └── user_b1  (is_admin=False, parent_id=company_b.username)  ← owns case_b1

Authorization is delegated to OpenFGA. These tests verify:
  - _get_case_db_or_404 (still a local helper)
  - require_permission dependency raises 403 when OpenFGA denies access
  - require_permission dependency passes when OpenFGA grants access
"""

import http
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.api.v1.case.case import _get_case_db_or_404
from src.api.v1.case.models import CaseDB
from src.api.v1.company.models import CompanyDB
from src.api.v1.user.models import User, UserDB

# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _make_user(db, *, username, is_admin, parent_id=None):  # noqa ANN001
    """Insert a UserDB row with the given attributes and return the ORM instance."""
    row = UserDB(
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


def _make_company(db):  # noqa ANN001
    """Insert a minimal CompanyDB row and return its UUID string."""
    cid = str(uuid.uuid4())
    db.add(CompanyDB(id=cid, name="Test Co", created_at=datetime.now(timezone.utc)))
    db.flush()
    return cid


def _make_case(db, *, cid, user_id, company_id, customer="Acme"):  # noqa ANN001
    """Insert a CaseDB row owned by user_id and return the ORM instance."""
    row = CaseDB(
        id=cid,
        responsible_person="Test Person",
        status="open",
        customer=customer,
        company_id=company_id,
        created_at=datetime.now(timezone.utc),
        user_id=user_id,
    )
    db.add(row)
    db.flush()
    return row


def _as_user(row):  # noqa ANN001
    """Convert a UserDB ORM row to the User Pydantic model used by auth."""
    return User(
        username=row.username,
        email=row.email,
        full_name=row.full_name,
        is_admin=row.is_admin,
        parent_id=row.parent_id,
    )


@pytest.fixture
def scenario(db):  # noqa ANN001
    """Create the full user/case hierarchy and return named references."""
    company_id = _make_company(db)

    super_admin = _make_user(db, username="superadmin", is_admin=True)
    company_a = _make_user(db, username="company_a", is_admin=True, parent_id=super_admin.username)
    company_b = _make_user(db, username="company_b", is_admin=True, parent_id=super_admin.username)
    user_a1 = _make_user(db, username="user_a1", is_admin=False, parent_id=company_a.username)
    user_a2 = _make_user(db, username="user_a2", is_admin=False, parent_id=company_a.username)
    user_b1 = _make_user(db, username="user_b1", is_admin=False, parent_id=company_b.username)

    case_a1 = _make_case(db, cid=str(uuid.uuid4()), user_id=user_a1.username, company_id=company_id)
    case_a2 = _make_case(db, cid=str(uuid.uuid4()), user_id=user_a2.username, company_id=company_id)
    case_b1 = _make_case(db, cid=str(uuid.uuid4()), user_id=user_b1.username, company_id=company_id)

    return {
        "db": db,
        "super_admin": super_admin,
        "company_a": company_a,
        "company_b": company_b,
        "user_a1": user_a1,
        "user_a2": user_a2,
        "user_b1": user_b1,
        "case_a1": case_a1,
        "case_a2": case_a2,
        "case_b1": case_b1,
    }


# ─── _get_case_db_or_404 ──────────────────────────────────────────────────────


def test_get_case_db_returns_row_when_found(scenario):  # noqa ANN001
    """Returns the CaseDB row when the case ID exists."""
    s = scenario
    row = _get_case_db_or_404(s["db"], s["case_a1"].id)
    assert row.id == s["case_a1"].id
    assert row.user_id == s["user_a1"].username


def test_get_case_db_raises_404_when_not_found(scenario):  # noqa ANN001
    """Raises 404 when no case exists for the given ID."""
    s = scenario
    with pytest.raises(HTTPException) as exc:
        _get_case_db_or_404(s["db"], str(uuid.uuid4()))
    assert exc.value.status_code == http.HTTPStatus.NOT_FOUND


# ─── require_permission dependency ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_permission_passes_when_fga_allows(scenario):  # noqa ANN001
    """Dependency does not raise when OpenFGA returns allowed=True."""
    s = scenario
    user = _as_user(s["user_a1"])

    with patch("src.api.v1.auth.fga.check_permission", new=AsyncMock(return_value=True)):
        from src.api.v1.auth.fga import require_permission
        checker = require_permission("viewer")
        result = await checker(case_id=s["case_a1"].id, current_user=user)
        assert result == user


@pytest.mark.asyncio
async def test_require_permission_raises_403_when_fga_denies(scenario):  # noqa ANN001
    """Dependency raises 403 when OpenFGA returns allowed=False."""
    s = scenario
    user = _as_user(s["user_b1"])

    with patch("src.api.v1.auth.fga.check_permission", new=AsyncMock(return_value=False)):
        from src.api.v1.auth.fga import require_permission
        checker = require_permission("viewer")
        with pytest.raises(HTTPException) as exc:
            await checker(case_id=s["case_a1"].id, current_user=user)
        assert exc.value.status_code == http.HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_require_permission_editor_passes_when_fga_allows(scenario):  # noqa ANN001
    """Editor permission check passes when OpenFGA allows it."""
    s = scenario
    user = _as_user(s["user_a1"])

    with patch("src.api.v1.auth.fga.check_permission", new=AsyncMock(return_value=True)):
        from src.api.v1.auth.fga import require_permission
        checker = require_permission("editor")
        result = await checker(case_id=s["case_a1"].id, current_user=user)
        assert result == user


@pytest.mark.asyncio
async def test_require_permission_editor_raises_403_when_fga_denies(scenario):  # noqa ANN001
    """Editor permission check raises 403 when OpenFGA denies it."""
    s = scenario
    user = _as_user(s["user_a2"])

    with patch("src.api.v1.auth.fga.check_permission", new=AsyncMock(return_value=False)):
        from src.api.v1.auth.fga import require_permission
        checker = require_permission("editor")
        with pytest.raises(HTTPException) as exc:
            await checker(case_id=s["case_a1"].id, current_user=user)
        assert exc.value.status_code == http.HTTPStatus.FORBIDDEN


# ─── filter_by_permission ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_filter_by_permission_returns_allowed_cases(scenario):  # noqa ANN001
    """Only cases the user has viewer access to are returned."""
    s = scenario
    from src.api.v1.auth.fga import filter_by_permission
    from src.api.v1.case.models import Case

    cases = [
        Case(id=s["case_a1"].id, responsible_person="A", status="open", customer="X",
             company_id=s["case_a1"].company_id, created_at="2024-01-01", updated_at=None),
        Case(id=s["case_b1"].id, responsible_person="B", status="open", customer="Y",
             company_id=s["case_b1"].company_id, created_at="2024-01-01", updated_at=None),
    ]

    from unittest.mock import MagicMock
    allowed = MagicMock(allowed=True, correlation_id=s["case_a1"].id)
    denied = MagicMock(allowed=False, correlation_id=s["case_b1"].id)
    mock_response = MagicMock(result=[allowed, denied])

    mock_client = AsyncMock()
    mock_client.batch_check = AsyncMock(return_value=mock_response)

    with patch("src.api.v1.auth.fga.get_fga_client", new=AsyncMock(return_value=mock_client)):
        result = await filter_by_permission(cases, s["user_a1"].username)
        assert len(result) == 1
        assert result[0].id == s["case_a1"].id


@pytest.mark.asyncio
async def test_filter_by_permission_empty_input():  # noqa ANN001
    """Returns empty list immediately without calling OpenFGA."""
    with patch("src.api.v1.auth.fga.get_fga_client") as mock_get:
        from src.api.v1.auth.fga import filter_by_permission
        result = await filter_by_permission([], "user-id")
        assert result == []
        mock_get.assert_not_called()
