"""Tests for case-level authorization logic (_authorize_case_access).

Hierarchy used across all tests:
  super_admin  (is_admin=True,  parent_id=None)
  ├── company_a  (is_admin=True,  parent_id=super_admin.id)
  │   ├── user_a1  (is_admin=False, parent_id=company_a.id)  ← owns case_a1
  │   └── user_a2  (is_admin=False, parent_id=company_a.id)  ← owns case_a2
  └── company_b  (is_admin=True,  parent_id=super_admin.id)
      └── user_b1  (is_admin=False, parent_id=company_b.id)  ← owns case_b1
"""

import http
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from src.api.v1.case.case import _authorize_case_access, _get_case_db_or_404
from src.api.v1.case.models import CaseDB
from src.api.v1.company.models import CompanyDB
from src.api.v1.user.models import User, UserDB

# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _make_user(db, *, uid, username, is_admin, parent_id=None):
    """Insert a UserDB row with the given attributes and return the ORM instance."""
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


def _make_company(db):
    """Insert a minimal CompanyDB row and return its UUID string."""
    cid = str(uuid.uuid4())
    db.add(CompanyDB(id=cid, name="Test Co", created_at=datetime.now(timezone.utc)))
    db.flush()
    return cid


def _make_case(db, *, cid, user_id, company_id, customer="Acme"):
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


def _as_user(row):
    """Convert a UserDB ORM row to the User Pydantic model used by auth."""
    return User(
        id=row.id,
        username=row.username,
        email=row.email,
        full_name=row.full_name,
        is_admin=row.is_admin,
        parent_id=row.parent_id,
    )


@pytest.fixture
def scenario(db):
    """Create the full user/case hierarchy and yield named references."""
    company_id = _make_company(db)

    super_admin = _make_user(db, uid=str(uuid.uuid4()), username="superadmin", is_admin=True)
    company_a = _make_user(db, uid=str(uuid.uuid4()), username="company_a", is_admin=True, parent_id=super_admin.id)
    company_b = _make_user(db, uid=str(uuid.uuid4()), username="company_b", is_admin=True, parent_id=super_admin.id)
    user_a1 = _make_user(db, uid=str(uuid.uuid4()), username="user_a1", is_admin=False, parent_id=company_a.id)
    user_a2 = _make_user(db, uid=str(uuid.uuid4()), username="user_a2", is_admin=False, parent_id=company_a.id)
    user_b1 = _make_user(db, uid=str(uuid.uuid4()), username="user_b1", is_admin=False, parent_id=company_b.id)

    case_a1 = _make_case(db, cid=str(uuid.uuid4()), user_id=user_a1.id, company_id=company_id)
    case_a2 = _make_case(db, cid=str(uuid.uuid4()), user_id=user_a2.id, company_id=company_id)
    case_b1 = _make_case(db, cid=str(uuid.uuid4()), user_id=user_b1.id, company_id=company_id)

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


# ─── Super admin ──────────────────────────────────────────────────────────────


def test_super_admin_can_access_company_a_case(scenario):
    """Super admin is allowed to access any case regardless of company."""
    s = scenario
    _authorize_case_access(s["db"], s["case_a1"], _as_user(s["super_admin"]))


def test_super_admin_can_access_company_b_case(scenario):
    """Super admin can access cases from a different company than company_a."""
    s = scenario
    _authorize_case_access(s["db"], s["case_b1"], _as_user(s["super_admin"]))


# ─── Company admin ────────────────────────────────────────────────────────────


def test_company_a_admin_can_access_own_sub_user_case(scenario):
    """Company admin can access a case owned by a direct sub-user."""
    s = scenario
    _authorize_case_access(s["db"], s["case_a1"], _as_user(s["company_a"]))


def test_company_a_admin_can_access_all_sub_users_in_company(scenario):
    """Company admin can access cases owned by any sub-user in their company."""
    s = scenario
    _authorize_case_access(s["db"], s["case_a2"], _as_user(s["company_a"]))


def test_company_a_admin_cannot_access_company_b_case(scenario):
    """Company admin is denied access to cases belonging to a different company."""
    s = scenario
    with pytest.raises(HTTPException) as exc:
        _authorize_case_access(s["db"], s["case_b1"], _as_user(s["company_a"]))
    assert exc.value.status_code == http.HTTPStatus.FORBIDDEN


def test_company_b_admin_cannot_access_company_a_case(scenario):
    """Company B admin cannot cross company boundaries to access company A's cases."""
    s = scenario
    with pytest.raises(HTTPException) as exc:
        _authorize_case_access(s["db"], s["case_a1"], _as_user(s["company_b"]))
    assert exc.value.status_code == http.HTTPStatus.FORBIDDEN


# ─── Regular user ─────────────────────────────────────────────────────────────


def test_user_can_access_own_case(scenario):
    """A regular user can always access their own case."""
    s = scenario
    _authorize_case_access(s["db"], s["case_a1"], _as_user(s["user_a1"]))


def test_user_can_access_colleague_case_same_company(scenario):
    """user_a1 can read a case owned by user_a2 (same company)."""
    s = scenario
    _authorize_case_access(s["db"], s["case_a2"], _as_user(s["user_a1"]))


def test_user_cannot_access_case_from_other_company(scenario):
    """A regular user cannot access a case owned by a user in a different company."""
    s = scenario
    with pytest.raises(HTTPException) as exc:
        _authorize_case_access(s["db"], s["case_b1"], _as_user(s["user_a1"]))
    assert exc.value.status_code == http.HTTPStatus.FORBIDDEN


def test_user_b_cannot_access_company_a_case(scenario):
    """user_b1 is denied access to a case owned by a user in company A."""
    s = scenario
    with pytest.raises(HTTPException) as exc:
        _authorize_case_access(s["db"], s["case_a1"], _as_user(s["user_b1"]))
    assert exc.value.status_code == http.HTTPStatus.FORBIDDEN


# ─── _get_case_db_or_404 ─────────────────────────────────────────────────────


def test_get_case_db_returns_row_when_found(scenario):
    """Returns the CaseDB row when the case ID exists."""
    s = scenario
    row = _get_case_db_or_404(s["db"], s["case_a1"].id)
    assert row.id == s["case_a1"].id
    assert row.user_id == s["user_a1"].id


def test_get_case_db_raises_404_when_not_found(scenario):
    """Raises 404 when no case exists for the given ID."""
    s = scenario
    with pytest.raises(HTTPException) as exc:
        _get_case_db_or_404(s["db"], str(uuid.uuid4()))
    assert exc.value.status_code == http.HTTPStatus.NOT_FOUND
