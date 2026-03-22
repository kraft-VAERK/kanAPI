"""Tests for customer profile features: extended company fields, single-company endpoint.

Hierarchy:
  super_admin  (is_admin=True,  parent_id=None)
  company_admin (is_admin=True, parent_id=super_admin)
  ├── sub_user_1  (is_admin=False, parent_id=company_admin)
  └── sub_user_2  (is_admin=False, parent_id=company_admin)
  owner_co  (company, owner_id=None)  — has ceo, business_number, hq_origin
  ├── client_a  (company, owner_id=owner_co)  — has cases
  └── client_b  (company, owner_id=owner_co)  — has cases
"""

import uuid
from datetime import datetime, timezone

import pytest

from src.api.v1.case.models import CaseDB, _apply_case_filters
from src.api.v1.company.models import (
    CompanyCreate,
    CompanyDB,
    db_create_company,
    db_get_company,
)
from src.api.v1.user.models import UserDB

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_user(db, *, username, is_admin, parent_id=None) -> str:  # noqa: ANN001
    """Insert a UserDB row and return its username."""
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


def _make_company(
    db, *, name, owner_id=None, email=None, phone=None, address=None, ceo=None, business_number=None, hq_origin=None,  # noqa: ANN001
) -> str:
    """Insert a CompanyDB row and return its UUID string."""
    cid = str(uuid.uuid4())
    db.add(
        CompanyDB(
            id=cid,
            name=name,
            email=email or f"{name.lower().replace(' ', '')}@test.dev",
            phone=phone,
            address=address,
            ceo=ceo,
            business_number=business_number,
            hq_origin=hq_origin,
            owner_id=owner_id,
            created_at=datetime.now(timezone.utc),
        ),
    )
    db.flush()
    return cid


def _make_case(
    db, *, user_id, company_id, customer, status="open", responsible="Tester", responsible_user_id=None,  # noqa: ANN001
) -> str:
    """Insert a CaseDB row and return its UUID string."""
    cid = str(uuid.uuid4())
    db.add(
        CaseDB(
            id=cid,
            responsible_person=responsible,
            responsible_user_id=responsible_user_id or user_id,
            status=status,
            customer=customer,
            company_id=company_id,
            created_at=datetime.now(timezone.utc),
            user_id=user_id,
        ),
    )
    db.flush()
    return cid


# ─── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture
def profile_scenario(db) -> dict:  # noqa: ANN001
    """Build hierarchy for customer profile testing."""
    super_admin = _make_user(db, username="sa_prof", is_admin=True)
    company_admin = _make_user(db, username="ca_prof", is_admin=True, parent_id=super_admin)
    sub1 = _make_user(db, username="sub1_prof", is_admin=False, parent_id=company_admin)
    sub2 = _make_user(db, username="sub2_prof", is_admin=False, parent_id=company_admin)

    owner_co = _make_company(
        db,
        name="Profile Owner Co",
        email="owner@profile.dev",
        phone="+1-555-0001",
        address="100 Main St",
        ceo="Jane Doe",
        business_number="POC-2024-001",
        hq_origin="New York, NY",
    )
    client_a = _make_company(
        db,
        name="Profile Client A",
        owner_id=owner_co,
        ceo="John Smith",
        business_number="PCA-2024-002",
        hq_origin="Boston, MA",
    )
    client_b = _make_company(
        db,
        name="Profile Client B",
        owner_id=owner_co,
        ceo="Bob Jones",
        hq_origin="Chicago, IL",
    )

    # Cases across client companies with overlapping customer names
    # Client A: 3 cases for "Acme Corp", 2 for "Wayne Ent"
    cases = {}
    cases["a_acme_1"] = _make_case(db, user_id=sub1, company_id=client_a, customer="Acme Corp")
    cases["a_acme_2"] = _make_case(db, user_id=sub1, company_id=client_a, customer="Acme Corp", status="closed")
    cases["a_acme_3"] = _make_case(db, user_id=sub2, company_id=client_a, customer="Acme Corp", status="pending")
    cases["a_wayne_1"] = _make_case(db, user_id=sub1, company_id=client_a, customer="Wayne Ent")
    cases["a_wayne_2"] = _make_case(db, user_id=sub2, company_id=client_a, customer="Wayne Ent", status="closed")

    # Client B: 2 cases for "Acme Corp", 1 for "Stark Ltd"
    cases["b_acme_1"] = _make_case(db, user_id=sub1, company_id=client_b, customer="Acme Corp")
    cases["b_acme_2"] = _make_case(db, user_id=sub2, company_id=client_b, customer="Acme Corp", status="in_progress")
    cases["b_stark_1"] = _make_case(db, user_id=sub1, company_id=client_b, customer="Stark Ltd")

    return {
        "db": db,
        "super_admin": super_admin,
        "company_admin": company_admin,
        "sub1": sub1,
        "sub2": sub2,
        "owner_co": owner_co,
        "client_a": client_a,
        "client_b": client_b,
        "cases": cases,
    }


# ─── Extended company fields (ceo, business_number, hq_origin) ──────────────


def test_company_new_fields_persisted(profile_scenario) -> None:  # noqa: ANN001
    """New company fields (ceo, business_number, hq_origin) are stored and retrievable."""
    s = profile_scenario
    company = db_get_company(s["db"], s["owner_co"])
    assert company is not None
    assert company.ceo == "Jane Doe"
    assert company.business_number == "POC-2024-001"
    assert company.hq_origin == "New York, NY"


def test_company_new_fields_nullable(profile_scenario) -> None:  # noqa: ANN001
    """New fields default to None when not provided."""
    s = profile_scenario
    cid = _make_company(s["db"], name="Bare Co")
    company = db_get_company(s["db"], cid)
    assert company is not None
    assert company.ceo is None
    assert company.business_number is None
    assert company.hq_origin is None


def test_create_company_with_new_fields(profile_scenario) -> None:  # noqa: ANN001
    """db_create_company persists ceo, business_number, and hq_origin."""
    s = profile_scenario
    result = db_create_company(
        s["db"],
        CompanyCreate(
            name="Full Profile Co",
            email="full@profile.dev",
            phone="+1-555-9999",
            address="42 Test Blvd",
            ceo="Ada Lovelace",
            business_number="FPC-2024-099",
            hq_origin="London, UK",
        ),
    )
    assert result.ceo == "Ada Lovelace"
    assert result.business_number == "FPC-2024-099"
    assert result.hq_origin == "London, UK"
    # Verify round-trip from DB
    fetched = db_get_company(s["db"], result.id)
    assert fetched.ceo == "Ada Lovelace"


def test_create_company_without_new_fields(profile_scenario) -> None:  # noqa: ANN001
    """db_create_company works when new fields are omitted."""
    s = profile_scenario
    result = db_create_company(s["db"], CompanyCreate(name="Minimal Co"))
    assert result.ceo is None
    assert result.business_number is None
    assert result.hq_origin is None


def test_client_company_has_new_fields(profile_scenario) -> None:  # noqa: ANN001
    """Client companies can also have ceo, business_number, hq_origin."""
    s = profile_scenario
    client_a = db_get_company(s["db"], s["client_a"])
    assert client_a.ceo == "John Smith"
    assert client_a.business_number == "PCA-2024-002"
    assert client_a.hq_origin == "Boston, MA"


def test_client_company_partial_new_fields(profile_scenario) -> None:  # noqa: ANN001
    """Client company with only some new fields set; others are None."""
    s = profile_scenario
    client_b = db_get_company(s["db"], s["client_b"])
    assert client_b.ceo == "Bob Jones"
    assert client_b.business_number is None
    assert client_b.hq_origin == "Chicago, IL"


# ─── GET /company/{company_id} (via db_get_company) ─────────────────────────


def test_get_company_returns_all_fields(profile_scenario) -> None:  # noqa: ANN001
    """db_get_company returns company with all fields including new ones."""
    s = profile_scenario
    company = db_get_company(s["db"], s["owner_co"])
    assert company is not None
    assert company.name == "Profile Owner Co"
    assert company.email == "owner@profile.dev"
    assert company.phone == "+1-555-0001"
    assert company.address == "100 Main St"
    assert company.ceo == "Jane Doe"
    assert company.business_number == "POC-2024-001"
    assert company.hq_origin == "New York, NY"
    assert company.created_at is not None


def test_get_company_not_found(profile_scenario) -> None:  # noqa: ANN001
    """db_get_company returns None for non-existent company."""
    s = profile_scenario
    assert db_get_company(s["db"], str(uuid.uuid4())) is None


def test_get_company_client_has_owner_id(profile_scenario) -> None:  # noqa: ANN001
    """db_get_company for a client company includes owner_id."""
    s = profile_scenario
    client = db_get_company(s["db"], s["client_a"])
    assert client is not None
    assert client.owner_id == s["owner_co"]


def test_get_company_owner_has_no_owner_id(profile_scenario) -> None:  # noqa: ANN001
    """db_get_company for an owner company has owner_id=None."""
    s = profile_scenario
    owner = db_get_company(s["db"], s["owner_co"])
    assert owner is not None
    assert owner.owner_id is None


# ─── Company cases: super admin sees client-company cases ────────────────────


def _super_admin_company_cases(db, company_id, q=None, status=None, archived=None) -> list:  # noqa: ANN001
    """Simulate GET /company/{id}/cases for super admin (includes client companies)."""
    client_ids = [r.id for r in db.query(CompanyDB).filter(CompanyDB.owner_id == company_id).all()]
    all_ids = [company_id, *client_ids]
    query = db.query(CaseDB).filter(CaseDB.company_id.in_(all_ids))
    query = _apply_case_filters(query, q=q, status=status, archived=archived)
    return query.all()


def _non_super_company_cases(db, company_id, q=None, status=None, archived=None) -> list:  # noqa: ANN001
    """Simulate GET /company/{id}/cases for non-super-admin (exact company only)."""
    query = db.query(CaseDB).filter(CaseDB.company_id == company_id)
    query = _apply_case_filters(query, q=q, status=status, archived=archived)
    return query.all()


def test_super_admin_sees_owner_plus_client_cases(profile_scenario) -> None:  # noqa: ANN001
    """Super admin querying owner company sees cases from all client companies."""
    s = profile_scenario
    cases = _super_admin_company_cases(s["db"], s["owner_co"])
    assert len(cases) == 8  # 5 in client_a + 3 in client_b


def test_super_admin_client_company_no_expansion(profile_scenario) -> None:  # noqa: ANN001
    """Super admin querying a client company only sees that company's cases (no sub-clients)."""
    s = profile_scenario
    cases = _super_admin_company_cases(s["db"], s["client_a"])
    assert len(cases) == 5  # only client_a cases


def test_non_super_sees_exact_company_only(profile_scenario) -> None:  # noqa: ANN001
    """Non-super-admin sees only cases for the exact company_id."""
    s = profile_scenario
    cases = _non_super_company_cases(s["db"], s["client_a"])
    assert len(cases) == 5
    assert all(c.company_id == s["client_a"] for c in cases)


def test_non_super_other_company_cases_isolated(profile_scenario) -> None:  # noqa: ANN001
    """Non-super-admin querying client_b sees only client_b cases."""
    s = profile_scenario
    cases = _non_super_company_cases(s["db"], s["client_b"])
    assert len(cases) == 3
    assert all(c.company_id == s["client_b"] for c in cases)


# ─── Customer name filtering (profile page behaviour) ────────────────────────


def test_filter_by_customer_name_within_company(profile_scenario) -> None:  # noqa: ANN001
    """Filtering cases by customer name within a single company returns correct count."""
    s = profile_scenario
    all_cases = _non_super_company_cases(s["db"], s["client_a"])
    acme_cases = [c for c in all_cases if c.customer == "Acme Corp"]
    wayne_cases = [c for c in all_cases if c.customer == "Wayne Ent"]
    assert len(acme_cases) == 3
    assert len(wayne_cases) == 2


def test_same_customer_different_companies_have_different_counts(profile_scenario) -> None:  # noqa: ANN001
    """Same customer name in different companies yields different case counts."""
    s = profile_scenario
    client_a_acme = [c for c in _non_super_company_cases(s["db"], s["client_a"]) if c.customer == "Acme Corp"]
    client_b_acme = [c for c in _non_super_company_cases(s["db"], s["client_b"]) if c.customer == "Acme Corp"]
    assert len(client_a_acme) == 3
    assert len(client_b_acme) == 2


def test_customer_company_key_produces_unique_rows(profile_scenario) -> None:  # noqa: ANN001
    """Keying customers by (name, company_id) creates distinct rows — mirrors frontend deriveClients."""
    s = profile_scenario
    all_cases = _super_admin_company_cases(s["db"], s["owner_co"])
    customer_map = {}
    for c in all_cases:
        key = f"{c.customer}\0{c.company_id}"
        if key not in customer_map:
            customer_map[key] = {"name": c.customer, "count": 0, "company_id": c.company_id}
        customer_map[key]["count"] += 1
    rows = list(customer_map.values())
    # "Acme Corp" appears in both client_a and client_b → 2 rows
    acme_rows = [r for r in rows if r["name"] == "Acme Corp"]
    assert len(acme_rows) == 2
    acme_counts = sorted(r["count"] for r in acme_rows)
    assert acme_counts == [2, 3]  # client_b has 2, client_a has 3


def test_customer_count_matches_profile_page_count(profile_scenario) -> None:  # noqa: ANN001
    """Count from deriveClients key matches what profile page would show after filtering."""
    s = profile_scenario
    # Simulate what the clients tab derives
    all_cases = _super_admin_company_cases(s["db"], s["owner_co"])
    customer_map = {}
    for c in all_cases:
        key = f"{c.customer}\0{c.company_id}"
        if key not in customer_map:
            customer_map[key] = {"name": c.customer, "count": 0, "company_id": c.company_id}
        customer_map[key]["count"] += 1

    # For each derived customer row, verify the profile page would show the same count
    for row in customer_map.values():
        profile_cases = _non_super_company_cases(s["db"], row["company_id"])
        filtered = [c for c in profile_cases if c.customer == row["name"]]
        assert len(filtered) == row["count"], (
            f'Mismatch for {row["name"]} in company {row["company_id"]}: '
            f'clients tab says {row["count"]}, profile page shows {len(filtered)}'
        )


# ─── Cases filtering on company endpoint ─────────────────────────────────────


def test_company_cases_filter_by_q(profile_scenario) -> None:  # noqa: ANN001
    """Filter cases by customer name search within a company."""
    s = profile_scenario
    cases = _non_super_company_cases(s["db"], s["client_a"], q="acme")
    assert len(cases) == 3
    assert all("Acme" in c.customer for c in cases)


def test_company_cases_filter_by_status(profile_scenario) -> None:  # noqa: ANN001
    """Filter cases by status within a company."""
    s = profile_scenario
    cases = _non_super_company_cases(s["db"], s["client_a"], status="closed")
    assert len(cases) == 2  # a_acme_2, a_wayne_2


def test_company_cases_combined_filters(profile_scenario) -> None:  # noqa: ANN001
    """Combine q + status filters for company cases."""
    s = profile_scenario
    cases = _non_super_company_cases(s["db"], s["client_a"], q="acme", status="pending")
    assert len(cases) == 1
    assert cases[0].customer == "Acme Corp"
    assert cases[0].status == "pending"
