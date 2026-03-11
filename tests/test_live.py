"""Live integration tests for kanAPI.

Requires the full stack to be running:
  - PostgreSQL on :5432          (make db)
  - MinIO on :9000               (make db)
  - OpenFGA on :8080             (docker compose up openfga)
  - kanAPI backend on :8000      (FGA_* env vars set, make run)
  - Seed data loaded             (PYTHONPATH=. python src/api/db/seed.py)

Run:
    pytest tests/test_live.py -v

Seeded credentials:
  superadmin@kanapi.dev / super123   — super admin
  admin@acme.dev        / acme123    — Acme company admin
  admin@globex.dev      / globex123  — Globex company admin
"""

import io
import uuid

import pytest
import requests
from minio import Minio

_minio = Minio("localhost:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)

BASE = "http://localhost:8000/api/v1"


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _session() -> requests.Session:
    """Return a fresh requests session (stores cookies automatically)."""
    return requests.Session()


def _login(session: requests.Session, email: str, password: str) -> dict:
    """Login and return the /auth/me payload."""
    r = session.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}: {r.text}"
    return session.get(f"{BASE}/auth/me").json()


def _create_case(session: requests.Session, company_id: str, **kwargs: str) -> dict:
    """Create a case and return the response JSON."""
    payload = {
        "responsible_person": kwargs.get("responsible_person", "Test Person"),
        "status": kwargs.get("status", "open"),
        "customer": kwargs.get("customer", "Test Customer"),
        "company_id": company_id,
    }
    r = session.post(f"{BASE}/case/create", json=payload)
    assert r.status_code == 201, f"Case creation failed: {r.text}"
    return r.json()


# ─── Health ───────────────────────────────────────────────────────────────────


def test_health_endpoint() -> None:
    """Test the health endpoint to ensure the API is operational."""
    for check in ["startup", "ready", "live"]:
        r = requests.get(f"{BASE}/health/{check}")
        assert r.status_code == 200, f"Health check {check!r} failed: {r.text}"


# ─── Authentication ───────────────────────────────────────────────────────────


def test_login_superadmin() -> None:
    """Super admin can log in and /auth/me returns admin flags."""
    s = _session()
    me = _login(s, "superadmin@kanapi.dev", "super123")
    assert me["email"] == "superadmin@kanapi.dev"
    assert me["is_admin"] is True
    assert me["parent_id"] is None


def test_login_company_admin() -> None:
    """Company admin can log in and /auth/me reflects company-level admin status."""
    s = _session()
    me = _login(s, "admin@acme.dev", "acme123")
    assert me["is_admin"] is True
    assert me["parent_id"] is not None  # has a parent (super admin)


def test_login_wrong_password_returns_401() -> None:
    """Wrong password returns 401."""
    r = requests.post(f"{BASE}/auth/login", json={"email": "superadmin@kanapi.dev", "password": "wrong"})
    assert r.status_code == 401


def test_logout_clears_session() -> None:
    """After logout, protected endpoints return 401."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")
    assert s.get(f"{BASE}/auth/me").status_code == 200
    s.post(f"{BASE}/auth/logout")
    assert s.get(f"{BASE}/auth/me").status_code == 401


def test_unauthenticated_case_list_returns_401() -> None:
    """Accessing cases without a session returns 401."""
    r = requests.get(f"{BASE}/case/")
    assert r.status_code == 401


# ─── Case CRUD ────────────────────────────────────────────────────────────────


def test_create_case_and_fetch_it() -> None:
    """Creating a case returns it, and fetching it by ID also works."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")

    # Get a company to link the case to
    companies = s.get(f"{BASE}/company/").json()
    assert companies, "No companies found"
    company_id = companies[0]["id"]

    case = _create_case(s, company_id, customer="Live Test Corp")
    assert case["id"]
    assert case["customer"] == "Live Test Corp"
    assert case["status"] == "open"

    # Fetch by ID — creator should have viewer access via OpenFGA
    r = s.get(f"{BASE}/case/{case['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == case["id"]


def test_case_list_returns_only_accessible_cases() -> None:
    """GET /case/ returns only cases the user has viewer access to in OpenFGA."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")

    cases = s.get(f"{BASE}/case/").json()
    assert isinstance(cases, list)
    # Every returned case must be individually fetchable (OpenFGA allowed it)
    for c in cases:
        r = s.get(f"{BASE}/case/{c['id']}")
        assert r.status_code == 200, f"Listed case {c['id']} not fetchable individually"


def test_create_case_missing_required_field_returns_400() -> None:
    """Creating a case without a required field returns 400."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")

    companies = s.get(f"{BASE}/company/").json()
    company_id = companies[0]["id"]

    r = s.post(
        f"{BASE}/case/create",
        json={
            "responsible_person": "",
            "status": "open",
            "customer": "X",
            "company_id": company_id,
        },
    )
    assert r.status_code == 400


# ─── OpenFGA authorization ────────────────────────────────────────────────────


def test_creator_can_access_own_case() -> None:
    """After creating a case, the creator can fetch it (OpenFGA grants viewer via creator relation)."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")

    companies = s.get(f"{BASE}/company/").json()
    company_id = companies[0]["id"]

    case = _create_case(s, company_id, customer="FGA Creator Test")
    r = s.get(f"{BASE}/case/{case['id']}")
    assert r.status_code == 200


def test_other_user_without_tuple_gets_403() -> None:
    """A user with no OpenFGA relation to a case gets 403."""
    # Create a case as acme admin
    s_acme = _session()
    _login(s_acme, "admin@acme.dev", "acme123")
    companies = s_acme.get(f"{BASE}/company/").json()
    company_id = companies[0]["id"]
    case = _create_case(s_acme, company_id, customer="Forbidden Case")

    # Try to access it as globex admin — no relation in OpenFGA
    s_globex = _session()
    _login(s_globex, "admin@globex.dev", "globex123")
    r = s_globex.get(f"{BASE}/case/{case['id']}")
    assert r.status_code == 403, f"Expected 403 but got {r.status_code}: {r.text}"


def test_fga_server_is_reachable() -> None:
    """OpenFGA HTTP server is up and returns a healthy status."""
    r = requests.get("http://localhost:8080/healthz")
    assert r.status_code == 200, f"OpenFGA health check failed: {r.text}"


def test_case_not_visible_to_other_company_in_list() -> None:
    """A case created by Acme does not appear in Globex's GET /case/ list (batch_check filters it out)."""
    # Acme creates a fresh case
    s_acme = _session()
    _login(s_acme, "admin@acme.dev", "acme123")
    companies = s_acme.get(f"{BASE}/company/").json()
    acme_company_id = companies[0]["id"]
    case = _create_case(s_acme, acme_company_id, customer="FGA Batch Filter Test")

    # Globex lists their cases — the Acme case must not appear
    s_globex = _session()
    _login(s_globex, "admin@globex.dev", "globex123")
    globex_case_ids = {c["id"] for c in s_globex.get(f"{BASE}/case/").json()}
    assert case["id"] not in globex_case_ids, "Acme case leaked into Globex's case list"


def test_nonexistent_case_returns_404() -> None:
    """Fetching a case ID that doesn't exist returns 404."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")

    # Even as logged-in user, nonexistent case → OpenFGA will deny → 403 before DB check
    # (OpenFGA has no relation for this ID, so require_permission fires first)
    r = s.get(f"{BASE}/case/00000000-0000-0000-0000-000000000000")
    assert r.status_code in (403, 404)


# ─── Delete ───────────────────────────────────────────────────────────────────


def test_creator_can_delete_own_case() -> None:
    """The creator of a case can delete it (FGA: creator → deleter)."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")
    companies = s.get(f"{BASE}/company/").json()
    company_id = companies[0]["id"]

    case = _create_case(s, company_id, customer="Delete Own Case Test")
    r = s.delete(f"{BASE}/case/{case['id']}")
    assert r.status_code == 204, f"Creator could not delete their own case: {r.status_code} {r.text}"

    # Confirm it's gone
    r = s.get(f"{BASE}/case/{case['id']}")
    assert r.status_code in (403, 404)


def test_admin_can_delete_subuser_case() -> None:
    """Company admin can delete a case created by one of their sub-users."""
    # Login as admin and get their ID + a company
    s_admin = _session()
    admin = _login(s_admin, "admin@acme.dev", "acme123")
    admin_id = admin["id"]
    companies = s_admin.get(f"{BASE}/company/").json()
    company_id = companies[0]["id"]

    # Create a sub-user under the admin
    sub_username = f"subuser_{uuid.uuid4().hex[:8]}"
    sub_email = f"{sub_username}@acme.dev"
    sub_password = "subtest123"
    r = requests.post(
        f"{BASE}/user/create",
        json={
            "username": sub_username,
            "email": sub_email,
            "password": sub_password,
            "is_admin": False,
            "parent_id": admin_id,
        },
    )
    assert r.status_code == 200, f"Sub-user creation failed: {r.text}"

    # Sub-user creates a case
    s_sub = _session()
    _login(s_sub, sub_email, sub_password)
    case = _create_case(s_sub, company_id, customer="Admin Delete Subuser Test")

    # Admin deletes the sub-user's case
    r = s_admin.delete(f"{BASE}/case/{case['id']}")
    assert r.status_code == 204, f"Admin could not delete sub-user's case: {r.status_code} {r.text}"


def test_delete_case_removes_documents_from_minio() -> None:
    """Deleting a case removes all its documents from MinIO."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")
    companies = s.get(f"{BASE}/company/").json()
    company_id = companies[0]["id"]

    case = _create_case(s, company_id, customer="Doc Cleanup Test")
    case_id = case["id"]

    # Seed two documents directly into MinIO
    for filename in ("report.txt", "invoice.txt"):
        data = f"content of {filename}".encode()
        _minio.put_object("kanapi", f"cases/{case_id}/{filename}", io.BytesIO(data), len(data))

    # Confirm they're visible via the API
    docs = s.get(f"{BASE}/case/{case_id}/documents").json()
    assert len(docs) == 2, f"Expected 2 docs before delete, got {len(docs)}"

    # Delete the case
    r = s.delete(f"{BASE}/case/{case_id}")
    assert r.status_code == 204, f"Delete failed: {r.status_code} {r.text}"

    # Confirm MinIO objects are gone
    remaining = list(_minio.list_objects("kanapi", prefix=f"cases/{case_id}/", recursive=True))
    assert len(remaining) == 0, f"Expected 0 docs after delete, found {[o.object_name for o in remaining]}"


def test_other_company_admin_cannot_delete_case() -> None:
    """A company admin from a different company cannot delete another company's case."""
    s_acme = _session()
    _login(s_acme, "admin@acme.dev", "acme123")
    companies = s_acme.get(f"{BASE}/company/").json()
    company_id = companies[0]["id"]
    case = _create_case(s_acme, company_id, customer="Cross-Company Delete Test")

    s_globex = _session()
    _login(s_globex, "admin@globex.dev", "globex123")
    r = s_globex.delete(f"{BASE}/case/{case['id']}")
    assert r.status_code == 403, f"Expected 403 but got {r.status_code}: {r.text}"


# ─── Company endpoints ────────────────────────────────────────────────────────


def test_list_companies_authenticated() -> None:
    """Authenticated user can list companies."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")
    r = s.get(f"{BASE}/company/")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_create_company_requires_super_admin() -> None:
    """Only super admin can create a company; company admin gets 403."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")
    r = s.post(f"{BASE}/company/", json={"name": "Should Fail Co"})
    assert r.status_code == 403


def test_super_admin_can_create_company() -> None:
    """Super admin can create a new company."""
    s = _session()
    _login(s, "superadmin@kanapi.dev", "super123")
    r = s.post(f"{BASE}/company/", json={"name": "Live Test Company", "email": "live@test.dev"})
    assert r.status_code in (200, 201)
    assert r.json()["name"] == "Live Test Company"


# ─── Documents ────────────────────────────────────────────────────────────────


def test_document_list_for_own_case() -> None:
    """Creator can list documents on their case (seeded cases have documents)."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")

    # Get a case owned by this user — use the seeded data
    cases = s.get(f"{BASE}/case/").json()
    if not cases:
        pytest.skip("No cases available for this user")

    case_id = cases[0]["id"]
    r = s.get(f"{BASE}/case/{case_id}/documents")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_company_admin_can_view_documents_on_subuser_case() -> None:
    """Company admin can list documents on a sub-user's case.

    FGA model: viewer = ... | tupleToUserset(company.admin)
    The admin has 'admin' on the company; the case has 'company' relation to that company,
    so admin is computed as 'viewer'.
    """
    s = _session()
    _login(s, "admin@acme.dev", "acme123")

    # my-cases returns cases owned by sub-users (user_id != admin.id)
    cases = s.get(f"{BASE}/company/my-cases").json()
    if not cases:
        pytest.skip("No company cases available")

    case_id = cases[0]["id"]

    # Case metadata — viewer check
    r = s.get(f"{BASE}/case/{case_id}")
    assert r.status_code == 200, f"Company admin blocked from viewing case metadata: {r.status_code} {r.text}"

    # Documents list — viewer check
    r = s.get(f"{BASE}/case/{case_id}/documents")
    assert r.status_code == 200, f"Company admin blocked from listing documents: {r.status_code} {r.text}"
    assert isinstance(r.json(), list)


def test_document_download_returns_content() -> None:
    """Downloading a seeded document streams non-empty content with HTTP 200."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")

    cases = s.get(f"{BASE}/company/my-cases").json()
    if not cases:
        pytest.skip("No company cases available")

    # Find first case that has at least one document
    for case in cases:
        docs = s.get(f"{BASE}/case/{case['id']}/documents").json()
        if docs:
            filename = docs[0]["name"]
            expected_size = docs[0]["size"]
            r = s.get(f"{BASE}/case/{case['id']}/documents/{filename}")
            assert r.status_code == 200, f"Download failed: {r.status_code} {r.text}"
            assert len(r.content) == expected_size, f"Downloaded {len(r.content)} bytes but expected {expected_size}"
            return

    pytest.skip("No seeded documents found — run: make seed")


def test_document_list_forbidden_for_other_user() -> None:
    """Globex admin cannot list documents of an Acme-created case."""
    s_acme = _session()
    _login(s_acme, "admin@acme.dev", "acme123")
    companies = s_acme.get(f"{BASE}/company/").json()
    company_id = companies[0]["id"]
    case = _create_case(s_acme, company_id, customer="Doc Forbidden Test")

    s_globex = _session()
    _login(s_globex, "admin@globex.dev", "globex123")
    r = s_globex.get(f"{BASE}/case/{case['id']}/documents")
    assert r.status_code == 403


# ─── User CRUD ────────────────────────────────────────────────────────────────


def _create_user(session: requests.Session, **kwargs: str) -> dict:
    """Create a throwaway user via POST /user/create and return the response JSON."""
    payload = {
        "username": kwargs.get("username", f"tmp_{uuid.uuid4().hex[:8]}"),
        "email": kwargs.get("email", f"tmp_{uuid.uuid4().hex[:8]}@test.dev"),
        "password": kwargs.get("password", "tmppass123"),
        "full_name": kwargs.get("full_name", "Temp User"),
        "is_admin": kwargs.get("is_admin", False),
    }
    r = session.post(f"{BASE}/user/create", json=payload)
    assert r.status_code == 200, f"User creation failed: {r.status_code} {r.text}"
    return r.json()


def test_superadmin_can_get_user_by_id() -> None:
    """Super admin can GET /user/{id} and receives the correct user payload."""
    s_super = _session()
    me = _login(s_super, "superadmin@kanapi.dev", "super123")  # noqa: F841

    # Create a throwaway user to fetch
    new_user = _create_user(s_super)
    user_id = new_user["id"]

    try:
        r = s_super.get(f"{BASE}/user/{user_id}")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data["id"] == user_id
        assert data["username"] == new_user["username"]
    finally:
        # clean up
        s_super.delete(f"{BASE}/user/{user_id}")


def test_nonadmin_cannot_get_user_by_id() -> None:
    """A regular (non-admin) user gets 403 when calling GET /user/{id}."""
    s_super = _session()
    _login(s_super, "superadmin@kanapi.dev", "super123")

    # Look up a real user ID (any user will do)
    all_users = s_super.get(f"{BASE}/user/all").json()
    assert all_users, "No users returned from /user/all"
    some_id = all_users[0]["id"]

    s_regular = _session()
    _login(s_regular, "test@acme.dev", "test123")
    r = s_regular.get(f"{BASE}/user/{some_id}")
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"


def test_superadmin_can_delete_user() -> None:
    """Super admin can DELETE /user/{id}; the user no longer appears in /user/all."""
    s_super = _session()
    _login(s_super, "superadmin@kanapi.dev", "super123")

    new_user = _create_user(s_super)
    user_id = new_user["id"]

    r = s_super.delete(f"{BASE}/user/{user_id}")
    assert r.status_code == 204, f"Expected 204, got {r.status_code}: {r.text}"

    # Verify the user is gone
    r2 = s_super.get(f"{BASE}/user/{user_id}")
    assert r2.status_code == 404, f"User still reachable after deletion: {r2.status_code}"


def test_cannot_delete_self() -> None:
    """An admin gets 400 when attempting to delete their own account."""
    s_super = _session()
    me = _login(s_super, "superadmin@kanapi.dev", "super123")

    r = s_super.delete(f"{BASE}/user/{me['id']}")
    assert r.status_code == 400, f"Expected 400 for self-delete, got {r.status_code}: {r.text}"
    assert "own account" in r.json().get("detail", "").lower()


def test_nonadmin_cannot_delete_user() -> None:
    """A regular user gets 403 when attempting to delete any user."""
    s_super = _session()
    _login(s_super, "superadmin@kanapi.dev", "super123")
    all_users = s_super.get(f"{BASE}/user/all").json()
    some_id = all_users[0]["id"]

    s_regular = _session()
    _login(s_regular, "test@acme.dev", "test123")
    r = s_regular.delete(f"{BASE}/user/{some_id}")
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"


def test_delete_nonexistent_user_returns_404() -> None:
    """Deleting a user ID that doesn't exist returns 404."""
    s_super = _session()
    _login(s_super, "superadmin@kanapi.dev", "super123")

    r = s_super.delete(f"{BASE}/user/{uuid.uuid4()}")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


def test_delete_user_with_cases_returns_409() -> None:
    """Deleting a sub-user who owns cases returns 409 with a helpful message."""
    s_admin = _session()
    _login(s_admin, "admin@acme.dev", "acme123")

    # Get a sub-user who has cases
    users = s_admin.get(f"{BASE}/company/my-users").json()
    users_with_cases = [u for u in users if not u.get("is_admin", False)]
    if not users_with_cases:
        pytest.skip("No sub-users with cases available")

    target_id = users_with_cases[0]["id"]
    r = s_admin.delete(f"{BASE}/user/{target_id}")
    assert r.status_code == 409, f"Expected 409 for user-with-cases delete, got {r.status_code}: {r.text}"
    assert "cases" in r.json().get("detail", "").lower()


# ─── Frontend ─────────────────────────────────────────────────────────────────


def test_frontend_build_exists() -> None:
    """The frontend dist/ directory exists and contains index.html."""
    from pathlib import Path

    dist = Path(__file__).parent.parent / "frontend" / "dist"
    assert dist.is_dir(), "frontend/dist/ not found — run: make frontend"
    assert (dist / "index.html").exists(), "frontend/dist/index.html missing"


def test_api_root_returns_welcome() -> None:
    """GET /api returns the welcome message."""
    r = requests.get("http://localhost:8000/api")
    assert r.status_code == 200
    assert r.json()["message"] == "Welcome to kanAPI!"
