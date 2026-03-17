"""Unit tests for case search/filter on company endpoints.

Tests the _apply_case_filters helper and the filtering behaviour of
get_my_company_cases and get_company_cases (via direct DB queries that
mirror the endpoint logic, since endpoints need async + auth deps).

Hierarchy:
  super_admin  (is_admin=True,  parent_id=None)
  company_admin (is_admin=True, parent_id=super_admin)
  ├── sub_user_1  (is_admin=False, parent_id=company_admin)
  └── sub_user_2  (is_admin=False, parent_id=company_admin)
  owner_co  (company)
  ├── client_co  (company, owner_id=owner_co)
"""

import uuid
from datetime import datetime, timezone

import pytest

from src.api.v1.case.models import CaseDB, _apply_case_filters
from src.api.v1.company.models import CompanyDB
from src.api.v1.user.models import UserDB

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_user(db, *, username, is_admin, parent_id=None) -> str:  # noqa: ANN001
    """Insert a UserDB row."""
    db.add(
        UserDB(
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
    return username


def _make_company(db, *, name, owner_id=None) -> str:  # noqa: ANN001
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


def _make_case(db, *, user_id, company_id, customer, status="open", responsible="Tester", archived=False) -> str:  # noqa: ANN001
    """Insert a CaseDB row and return its UUID string."""
    cid = str(uuid.uuid4())
    db.add(
        CaseDB(
            id=cid,
            responsible_person=responsible,
            status=status,
            customer=customer,
            company_id=company_id,
            created_at=datetime.now(timezone.utc),
            user_id=user_id,
            archived=archived,
        ),
    )
    db.flush()
    return cid


# ─── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture
def search_scenario(db) -> dict:  # noqa: ANN001
    """Build a hierarchy with varied cases for search/filter testing."""
    super_admin = _make_user(db, username="sa_search", is_admin=True)
    company_admin = _make_user(db, username="ca_search", is_admin=True, parent_id=super_admin)
    sub1 = _make_user(db, username="sub1_search", is_admin=False, parent_id=company_admin)
    sub2 = _make_user(db, username="sub2_search", is_admin=False, parent_id=company_admin)

    owner_co = _make_company(db, name="Search Owner Co")
    client_co = _make_company(db, name="Search Client Co", owner_id=owner_co)

    # Cases with different statuses, customers, responsible persons, archived flags
    c1 = _make_case(
        db, user_id=sub1, company_id=owner_co, customer="Acme Corp", status="open", responsible="Alice",
    )
    c2 = _make_case(
        db, user_id=sub1, company_id=owner_co, customer="Globex Inc", status="closed", responsible="Bob",
    )
    c3 = _make_case(
        db, user_id=sub2, company_id=client_co, customer="Acme Corp", status="pending", responsible="Charlie",
    )
    c4 = _make_case(
        db, user_id=sub2, company_id=client_co, customer="Wayne Ent",
        status="open", responsible="Alice", archived=True,
    )
    c5 = _make_case(
        db, user_id=company_admin, company_id=owner_co, customer="Stark Ltd",
        status="in_progress", responsible="Diana",
    )

    return {
        "db": db,
        "super_admin": super_admin,
        "company_admin": company_admin,
        "sub1": sub1,
        "sub2": sub2,
        "owner_co": owner_co,
        "client_co": client_co,
        "case_ids": [c1, c2, c3, c4, c5],
    }


# ─── _apply_case_filters ─────────────────────────────────────────────────────


def test_filter_no_params_returns_all(search_scenario) -> None:  # noqa: ANN001
    """No filter params returns all cases in the query."""
    s = search_scenario
    query = s["db"].query(CaseDB)
    filtered = _apply_case_filters(query).all()
    assert len(filtered) >= 5


def test_filter_by_status(search_scenario) -> None:  # noqa: ANN001
    """Filtering by status returns only matching cases."""
    s = search_scenario
    query = s["db"].query(CaseDB).filter(CaseDB.id.in_(s["case_ids"]))
    filtered = _apply_case_filters(query, status="open").all()
    assert all(c.status == "open" for c in filtered)
    assert len(filtered) == 2  # c1 (open) + c4 (open, archived)


def test_filter_by_q_customer(search_scenario) -> None:  # noqa: ANN001
    """Free-text search matches customer name (case-insensitive)."""
    s = search_scenario
    query = s["db"].query(CaseDB).filter(CaseDB.id.in_(s["case_ids"]))
    filtered = _apply_case_filters(query, q="acme").all()
    assert len(filtered) == 2  # c1, c3 — both "Acme Corp"
    assert all("Acme" in c.customer for c in filtered)


def test_filter_by_q_responsible(search_scenario) -> None:  # noqa: ANN001
    """Free-text search matches responsible_person (case-insensitive)."""
    s = search_scenario
    query = s["db"].query(CaseDB).filter(CaseDB.id.in_(s["case_ids"]))
    filtered = _apply_case_filters(query, q="alice").all()
    assert len(filtered) == 2  # c1, c4 — both "Alice"
    assert all(c.responsible_person == "Alice" for c in filtered)


def test_filter_by_archived(search_scenario) -> None:  # noqa: ANN001
    """Filtering by archived=True returns only archived cases."""
    s = search_scenario
    query = s["db"].query(CaseDB).filter(CaseDB.id.in_(s["case_ids"]))
    filtered = _apply_case_filters(query, archived=True).all()
    assert len(filtered) == 1  # c4
    assert filtered[0].customer == "Wayne Ent"


def test_filter_by_archived_false(search_scenario) -> None:  # noqa: ANN001
    """Filtering by archived=False returns only non-archived cases."""
    s = search_scenario
    query = s["db"].query(CaseDB).filter(CaseDB.id.in_(s["case_ids"]))
    filtered = _apply_case_filters(query, archived=False).all()
    assert len(filtered) == 4  # c1, c2, c3, c5


def test_filter_combined_q_and_status(search_scenario) -> None:  # noqa: ANN001
    """Combining q + status narrows results to the intersection."""
    s = search_scenario
    query = s["db"].query(CaseDB).filter(CaseDB.id.in_(s["case_ids"]))
    filtered = _apply_case_filters(query, q="acme", status="open").all()
    assert len(filtered) == 1  # c1 only — "Acme Corp" + "open"


def test_filter_q_no_match(search_scenario) -> None:  # noqa: ANN001
    """Free-text search that matches nothing returns empty list."""
    s = search_scenario
    query = s["db"].query(CaseDB).filter(CaseDB.id.in_(s["case_ids"]))
    filtered = _apply_case_filters(query, q="nonexistent").all()
    assert len(filtered) == 0


# ─── Company admin: my-cases filtering (simulated) ───────────────────────────


def _company_admin_cases(db, company_admin, q=None, status=None, archived=None) -> list:  # noqa: ANN001
    """Simulate GET /company/my-cases with filters (mirrors endpoint logic)."""
    sub_user_ids = [u.username for u in db.query(UserDB).filter(UserDB.parent_id == company_admin).all()]
    all_user_ids = [company_admin, *sub_user_ids]
    query = db.query(CaseDB).filter(CaseDB.user_id.in_(all_user_ids))
    query = _apply_case_filters(query, q=q, status=status, archived=archived)
    return query.all()


def test_my_cases_no_filter(search_scenario) -> None:  # noqa: ANN001
    """Company admin sees all cases from self + sub-users without filters."""
    s = search_scenario
    cases = _company_admin_cases(s["db"], s["company_admin"])
    assert len(cases) == 5


def test_my_cases_filter_by_status(search_scenario) -> None:  # noqa: ANN001
    """Company admin filters cases by status."""
    s = search_scenario
    cases = _company_admin_cases(s["db"], s["company_admin"], status="closed")
    assert len(cases) == 1
    assert cases[0].status == "closed"


def test_my_cases_filter_by_q(search_scenario) -> None:  # noqa: ANN001
    """Company admin searches cases by customer name."""
    s = search_scenario
    cases = _company_admin_cases(s["db"], s["company_admin"], q="globex")
    assert len(cases) == 1
    assert cases[0].customer == "Globex Inc"


def test_my_cases_filter_by_archived(search_scenario) -> None:  # noqa: ANN001
    """Company admin filters archived cases."""
    s = search_scenario
    cases = _company_admin_cases(s["db"], s["company_admin"], archived=True)
    assert len(cases) == 1
    assert cases[0].archived is True


def test_my_cases_combined_filters(search_scenario) -> None:  # noqa: ANN001
    """Company admin combines q + status filters."""
    s = search_scenario
    cases = _company_admin_cases(s["db"], s["company_admin"], q="alice", status="open")
    # c1 (Alice, open, not archived) + c4 (Alice, open, archived)
    assert len(cases) == 2


# ─── Super admin: company cases filtering (simulated) ────────────────────────


def _super_admin_company_cases(db, company_id, q=None, status=None, archived=None) -> list:  # noqa: ANN001
    """Simulate GET /company/{id}/cases with filters (mirrors endpoint logic)."""
    client_ids = [r.id for r in db.query(CompanyDB).filter(CompanyDB.owner_id == company_id).all()]
    all_ids = [company_id, *client_ids]
    query = db.query(CaseDB).filter(CaseDB.company_id.in_(all_ids))
    query = _apply_case_filters(query, q=q, status=status, archived=archived)
    return query.all()


def test_company_cases_no_filter(search_scenario) -> None:  # noqa: ANN001
    """Super admin sees all cases for company + clients without filters."""
    s = search_scenario
    cases = _super_admin_company_cases(s["db"], s["owner_co"])
    # owner_co: c1, c2, c5; client_co (owned by owner_co): c3, c4
    assert len(cases) == 5


def test_company_cases_filter_by_status(search_scenario) -> None:  # noqa: ANN001
    """Super admin filters company cases by status."""
    s = search_scenario
    cases = _super_admin_company_cases(s["db"], s["owner_co"], status="pending")
    assert len(cases) == 1
    assert cases[0].customer == "Acme Corp"
    assert cases[0].status == "pending"


def test_company_cases_filter_by_q(search_scenario) -> None:  # noqa: ANN001
    """Super admin searches company cases by responsible person."""
    s = search_scenario
    cases = _super_admin_company_cases(s["db"], s["owner_co"], q="diana")
    assert len(cases) == 1
    assert cases[0].responsible_person == "Diana"


def test_company_cases_filter_by_archived(search_scenario) -> None:  # noqa: ANN001
    """Super admin filters archived company cases."""
    s = search_scenario
    cases = _super_admin_company_cases(s["db"], s["owner_co"], archived=False)
    assert len(cases) == 4  # all except c4


def test_company_cases_combined_filters(search_scenario) -> None:  # noqa: ANN001
    """Super admin combines q + status + archived filters."""
    s = search_scenario
    cases = _super_admin_company_cases(s["db"], s["owner_co"], q="acme", status="open", archived=False)
    assert len(cases) == 1  # c1 only


def test_company_cases_q_no_match(search_scenario) -> None:  # noqa: ANN001
    """Super admin search with no matches returns empty list."""
    s = search_scenario
    cases = _super_admin_company_cases(s["db"], s["owner_co"], q="zzz_no_match")
    assert len(cases) == 0
