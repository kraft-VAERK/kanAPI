"""Tests for company CRUD functions and access-control guards.

Hierarchy used across all tests:
  super_admin  (is_admin=True,  parent_id=None)
  ├── owner_co   (CompanyDB, owner_id=None)
  │   ├── client_a (CompanyDB, owner_id=owner_co.id)  ← has case_a
  │   └── client_b (CompanyDB, owner_id=owner_co.id)
  └── solo_co    (CompanyDB, owner_id=None)            ← no clients
  company_admin (is_admin=True,  parent_id=super_admin.id)
  regular_user  (is_admin=False, parent_id=company_admin.id)
"""

import http
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from src.api.v1.case.models import CaseDB
from src.api.v1.company.company import _require_company_admin, _require_super_admin
from src.api.v1.company.models import (
    CompanyCreate,
    CompanyDB,
    db_create_company,
    db_get_client_companies,
    db_get_companies,
    db_get_company,
)
from src.api.v1.user.models import User, UserDB

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_user(db, *, username, is_admin, parent_id=None):  # noqa ANN001
    """Insert a UserDB row and return its UUID string."""
    uid = str(uuid.uuid4())
    db.add(
        UserDB(
            id=uid,
            username=username,
            email=f"{username}@test.dev",
            full_name=username.title(),
            password="hashed",
            is_active=True,
            is_admin=is_admin,
            parent_id=parent_id,
        ),
    )
    db.flush()
    return uid


def _make_company(db, *, name, owner_id=None):  # noqa ANN001
    """Insert a CompanyDB row and return its UUID string."""
    cid = str(uuid.uuid4())
    db.add(
        CompanyDB(
            id=cid,
            name=name,
            email=f"{name.lower().replace(' ', '')}@test.dev",
            owner_id=owner_id,
            created_at=datetime.now(timezone.utc),
        ),
    )
    db.flush()
    return cid


def _as_user(db, uid):  # noqa ANN001
    """Load a UserDB row by ID and return a Pydantic User instance."""
    row = db.query(UserDB).filter(UserDB.id == uid).first()
    return User(
        id=row.id,
        username=row.username,
        email=row.email,
        is_admin=row.is_admin,
        parent_id=row.parent_id,
    )


# ─── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture
def scenario(db):  # noqa ANN001
    """Build the full user/company/case hierarchy used across all tests."""
    super_admin_id = _make_user(db, username="super", is_admin=True)
    company_admin_id = _make_user(db, username="cadmin", is_admin=True, parent_id=super_admin_id)
    regular_user_id = _make_user(db, username="user1", is_admin=False, parent_id=company_admin_id)

    owner_co_id = _make_company(db, name="Owner Co")
    client_a_id = _make_company(db, name="Client A", owner_id=owner_co_id)
    client_b_id = _make_company(db, name="Client B", owner_id=owner_co_id)
    solo_co_id = _make_company(db, name="Solo Co")

    # A case linked to client_a
    case_id = str(uuid.uuid4())
    db.add(
        CaseDB(
            id=case_id,
            responsible_person="Tester",
            status="open",
            customer="Test Customer",
            company_id=client_a_id,
            created_at=datetime.now(timezone.utc),
            user_id=regular_user_id,
        ),
    )
    db.flush()

    return {
        "db": db,
        "super_admin_id": super_admin_id,
        "company_admin_id": company_admin_id,
        "regular_user_id": regular_user_id,
        "owner_co_id": owner_co_id,
        "client_a_id": client_a_id,
        "client_b_id": client_b_id,
        "solo_co_id": solo_co_id,
        "case_id": case_id,
    }


# ─── db_create_company ────────────────────────────────────────────────────────


def test_create_company_minimal(scenario):  # noqa ANN001
    """Creates a company with only a name; owner_id defaults to None."""
    s = scenario
    result = db_create_company(s["db"], CompanyCreate(name="New Co"))
    assert result.id is not None
    assert result.name == "New Co"
    assert result.owner_id is None


def test_create_company_with_owner(scenario):  # noqa ANN001
    """Creates a client company linked to an owner company."""
    s = scenario
    result = db_create_company(s["db"], CompanyCreate(name="Child Co", owner_id=s["owner_co_id"]))
    assert result.owner_id == s["owner_co_id"]


def test_create_company_with_all_fields(scenario):  # noqa ANN001
    """Creates a company with all optional fields set and verifies they persist."""
    s = scenario
    result = db_create_company(
        s["db"],
        CompanyCreate(
            name="Full Co",
            email="full@co.dev",
            phone="+1-555-0100",
            address="1 Test Ave",
            owner_id=None,
        ),
    )
    assert result.email == "full@co.dev"
    assert result.phone == "+1-555-0100"
    assert result.address == "1 Test Ave"


# ─── db_get_companies ─────────────────────────────────────────────────────────


def test_get_companies_returns_all(scenario):  # noqa ANN001
    """Returns all companies in the database."""
    s = scenario
    results = db_get_companies(s["db"])
    ids = {r.id for r in results}
    assert s["owner_co_id"] in ids
    assert s["client_a_id"] in ids
    assert s["solo_co_id"] in ids


def test_get_companies_empty_after_none_created(db):  # noqa ANN001
    """Returns an empty list when no companies exist."""
    results = db_get_companies(db)
    assert results == []


# ─── db_get_company ───────────────────────────────────────────────────────────


def test_get_company_by_id(scenario):  # noqa ANN001
    """Fetches a company by its UUID and verifies the returned name."""
    s = scenario
    result = db_get_company(s["db"], s["owner_co_id"])
    assert result is not None
    assert result.name == "Owner Co"


def test_get_company_returns_none_for_missing(scenario):  # noqa ANN001
    """Returns None when the requested company ID does not exist."""
    s = scenario
    result = db_get_company(s["db"], str(uuid.uuid4()))
    assert result is None


# ─── db_get_client_companies ──────────────────────────────────────────────────


def test_get_client_companies_returns_children(scenario):  # noqa ANN001
    """Returns only direct client companies owned by the given company."""
    s = scenario
    clients = db_get_client_companies(s["db"], s["owner_co_id"])
    client_ids = {c.id for c in clients}
    assert s["client_a_id"] in client_ids
    assert s["client_b_id"] in client_ids
    assert s["solo_co_id"] not in client_ids


def test_get_client_companies_empty_for_leaf(scenario):  # noqa ANN001
    """Returns an empty list for a company that has no client children."""
    s = scenario
    clients = db_get_client_companies(s["db"], s["client_a_id"])
    assert clients == []


# ─── _require_super_admin ─────────────────────────────────────────────────────


def test_require_super_admin_passes(scenario):  # noqa ANN001
    """Does not raise for a super admin (is_admin=True, parent_id=None)."""
    s = scenario
    _require_super_admin(_as_user(s["db"], s["super_admin_id"]))  # no exception


def test_require_super_admin_rejects_company_admin(scenario):  # noqa ANN001
    """Raises 403 for a company admin (is_admin=True but parent_id is set)."""
    s = scenario
    with pytest.raises(HTTPException) as exc:
        _require_super_admin(_as_user(s["db"], s["company_admin_id"]))
    assert exc.value.status_code == http.HTTPStatus.FORBIDDEN


def test_require_super_admin_rejects_regular_user(scenario):  # noqa ANN001
    """Raises 403 for a regular user (is_admin=False)."""
    s = scenario
    with pytest.raises(HTTPException) as exc:
        _require_super_admin(_as_user(s["db"], s["regular_user_id"]))
    assert exc.value.status_code == http.HTTPStatus.FORBIDDEN


# ─── _require_company_admin ───────────────────────────────────────────────────


def test_require_company_admin_passes(scenario):  # noqa ANN001
    """Does not raise for a company admin (is_admin=True, parent_id set)."""
    s = scenario
    _require_company_admin(_as_user(s["db"], s["company_admin_id"]))  # no exception


def test_require_company_admin_rejects_super_admin(scenario):  # noqa ANN001
    """Raises 403 for a super admin (parent_id=None disqualifies company admin role)."""
    s = scenario
    with pytest.raises(HTTPException) as exc:
        _require_company_admin(_as_user(s["db"], s["super_admin_id"]))
    assert exc.value.status_code == http.HTTPStatus.FORBIDDEN


def test_require_company_admin_rejects_regular_user(scenario):  # noqa ANN001
    """Raises 403 for a regular user (is_admin=False)."""
    s = scenario
    with pytest.raises(HTTPException) as exc:
        _require_company_admin(_as_user(s["db"], s["regular_user_id"]))
    assert exc.value.status_code == http.HTTPStatus.FORBIDDEN
