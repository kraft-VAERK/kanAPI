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
    # Login as admin and get their username + a company
    s_admin = _session()
    admin = _login(s_admin, "admin@acme.dev", "acme123")
    admin_username = admin["username"]
    companies = s_admin.get(f"{BASE}/company/").json()
    company_id = companies[0]["id"]

    # Create a sub-user under the admin (requires admin auth)
    sub_username = f"subuser_{uuid.uuid4().hex[:8]}"
    sub_email = f"{sub_username}@acme.dev"
    sub_password = "subtest123"
    r = s_admin.post(
        f"{BASE}/user/create",
        json={
            "username": sub_username,
            "email": sub_email,
            "password": sub_password,
            "is_admin": False,
            "parent_id": admin_username,
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


# ─── Activity log ─────────────────────────────────────────────────────────────


def test_create_case_logs_case_created() -> None:
    """Creating a case writes a case_created activity entry."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")
    companies = s.get(f"{BASE}/company/").json()
    company_id = companies[0]["id"]

    case = _create_case(s, company_id, customer="Activity Log Test")
    try:
        r = s.get(f"{BASE}/case/{case['id']}/activity")
        assert r.status_code == 200, f"Activity fetch failed: {r.text}"
        entries = r.json()
        actions = [e["action"] for e in entries]
        assert "case_created" in actions, f"case_created not in activity: {actions}"
    finally:
        s.delete(f"{BASE}/case/{case['id']}")


def test_update_case_status_logs_status_changed() -> None:
    """PATCHing a case's status writes a status_changed activity entry with old→new detail."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")
    companies = s.get(f"{BASE}/company/").json()
    company_id = companies[0]["id"]

    case = _create_case(s, company_id, status="open", customer="Status Change Test")
    try:
        r = s.patch(f"{BASE}/case/{case['id']}", json={"status": "in_progress"})
        assert r.status_code == 200, f"PATCH failed: {r.text}"
        assert r.json()["status"] == "in_progress"

        activity = s.get(f"{BASE}/case/{case['id']}/activity").json()
        status_entry = next((e for e in activity if e["action"] == "status_changed"), None)
        assert status_entry is not None, f"status_changed not found in activity: {activity}"
        assert "open" in status_entry["detail"]
        assert "in_progress" in status_entry["detail"]
    finally:
        s.delete(f"{BASE}/case/{case['id']}")


def test_update_case_responsible_logs_responsible_changed() -> None:
    """PATCHing responsible_person writes a responsible_changed activity entry."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")
    companies = s.get(f"{BASE}/company/").json()
    company_id = companies[0]["id"]

    case = _create_case(s, company_id, responsible_person="Alice", customer="Responsible Change Test")
    try:
        r = s.patch(f"{BASE}/case/{case['id']}", json={"responsible_person": "Bob"})
        assert r.status_code == 200, f"PATCH failed: {r.text}"

        activity = s.get(f"{BASE}/case/{case['id']}/activity").json()
        entry = next((e for e in activity if e["action"] == "responsible_changed"), None)
        assert entry is not None, f"responsible_changed not found in activity: {activity}"
        assert "Alice" in entry["detail"]
        assert "Bob" in entry["detail"]
    finally:
        s.delete(f"{BASE}/case/{case['id']}")


def test_activity_forbidden_without_viewer_access() -> None:
    """User with no FGA relation to a case gets 403 on the activity endpoint."""
    s_acme = _session()
    _login(s_acme, "admin@acme.dev", "acme123")
    companies = s_acme.get(f"{BASE}/company/").json()
    company_id = companies[0]["id"]
    case = _create_case(s_acme, company_id, customer="Activity Access Test")
    try:
        s_globex = _session()
        _login(s_globex, "admin@globex.dev", "globex123")
        r = s_globex.get(f"{BASE}/case/{case['id']}/activity")
        assert r.status_code == 403, f"Expected 403 for unauthorized user, got {r.status_code}"
    finally:
        s_acme.delete(f"{BASE}/case/{case['id']}")


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


def test_delete_company_requires_super_admin() -> None:
    """Company admin and regular user get 403 when attempting to delete a company."""
    # Super admin creates a company to use as target
    s_super = _session()
    _login(s_super, "superadmin@kanapi.dev", "super123")
    r = s_super.post(f"{BASE}/company/", json={"name": "Delete Guard Test Co"})
    assert r.status_code in (200, 201)
    company_id = r.json()["id"]

    try:
        # Company admin gets 403
        s_admin = _session()
        _login(s_admin, "admin@acme.dev", "acme123")
        r = s_admin.delete(f"{BASE}/company/{company_id}")
        assert r.status_code == 403, f"Expected 403 for company admin, got {r.status_code}"

        # Regular user gets 403
        s_user = _session()
        _login(s_user, "test@acme.dev", "test123")
        r = s_user.delete(f"{BASE}/company/{company_id}")
        assert r.status_code == 403, f"Expected 403 for regular user, got {r.status_code}"
    finally:
        s_super.delete(f"{BASE}/company/{company_id}")


def test_delete_company_with_cases_returns_409() -> None:
    """Deleting a company that has cases attached returns 409 Conflict."""
    s = _session()
    _login(s, "superadmin@kanapi.dev", "super123")

    # Find a company that has cases
    companies = s.get(f"{BASE}/company/").json()
    for company in companies:
        cases = s.get(f"{BASE}/company/{company['id']}/cases").json()
        if cases:
            r = s.delete(f"{BASE}/company/{company['id']}")
            assert r.status_code == 409, f"Expected 409, got {r.status_code}: {r.text}"
            assert "case" in r.json().get("detail", "").lower()
            return

    pytest.skip("No company with cases found — run: make seed")


def test_super_admin_can_create_company() -> None:
    """Super admin can create a new company, then deletes it to leave no data behind."""
    s = _session()
    _login(s, "superadmin@kanapi.dev", "super123")
    r = s.post(f"{BASE}/company/", json={"name": "Live Test Company", "email": "live@test.dev"})
    assert r.status_code in (200, 201)
    company = r.json()
    assert company["name"] == "Live Test Company"
    try:
        r_del = s.delete(f"{BASE}/company/{company['id']}")
        assert r_del.status_code == 204, f"Cleanup delete failed: {r_del.status_code} {r_del.text}"
    finally:
        pass  # best-effort cleanup — failure here is non-fatal for the assertion above


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
    """Super admin can GET /user/{username} and receives the correct user payload."""
    s_super = _session()
    me = _login(s_super, "superadmin@kanapi.dev", "super123")  # noqa: F841

    # Create a throwaway user to fetch
    new_user = _create_user(s_super)
    username = new_user["username"]

    try:
        r = s_super.get(f"{BASE}/user/{username}")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data["username"] == username
    finally:
        # clean up
        s_super.delete(f"{BASE}/user/{username}")


def test_nonadmin_cannot_get_user_by_id() -> None:
    """A regular (non-admin) user gets 403 when calling GET /user/{username}."""
    s_super = _session()
    _login(s_super, "superadmin@kanapi.dev", "super123")

    all_users = s_super.get(f"{BASE}/user/all").json()
    assert all_users, "No users returned from /user/all"
    some_username = all_users[0]["username"]

    s_regular = _session()
    _login(s_regular, "test@acme.dev", "test123")
    r = s_regular.get(f"{BASE}/user/{some_username}")
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"


def test_superadmin_can_delete_user() -> None:
    """Super admin can DELETE /user/{username}; the user no longer appears in /user/all."""
    s_super = _session()
    _login(s_super, "superadmin@kanapi.dev", "super123")

    new_user = _create_user(s_super)
    username = new_user["username"]

    r = s_super.delete(f"{BASE}/user/{username}")
    assert r.status_code == 204, f"Expected 204, got {r.status_code}: {r.text}"

    # Verify the user is gone
    r2 = s_super.get(f"{BASE}/user/{username}")
    assert r2.status_code == 404, f"User still reachable after deletion: {r2.status_code}"


def test_cannot_delete_self() -> None:
    """An admin gets 400 when attempting to delete their own account."""
    s_super = _session()
    me = _login(s_super, "superadmin@kanapi.dev", "super123")

    r = s_super.delete(f"{BASE}/user/{me['username']}")
    assert r.status_code == 400, f"Expected 400 for self-delete, got {r.status_code}: {r.text}"
    assert "own account" in r.json().get("detail", "").lower()


def test_nonadmin_cannot_delete_user() -> None:
    """A regular user gets 403 when attempting to delete any user."""
    s_super = _session()
    _login(s_super, "superadmin@kanapi.dev", "super123")
    all_users = s_super.get(f"{BASE}/user/all").json()
    some_username = all_users[0]["username"]

    s_regular = _session()
    _login(s_regular, "test@acme.dev", "test123")
    r = s_regular.delete(f"{BASE}/user/{some_username}")
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"


def test_delete_nonexistent_user_returns_404() -> None:
    """Deleting a username that doesn't exist returns 404."""
    s_super = _session()
    _login(s_super, "superadmin@kanapi.dev", "super123")

    r = s_super.delete(f"{BASE}/user/nonexistent_user_{uuid.uuid4().hex[:8]}")
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

    target_username = users_with_cases[0]["username"]
    r = s_admin.delete(f"{BASE}/user/{target_username}")
    assert r.status_code == 409, f"Expected 409 for user-with-cases delete, got {r.status_code}: {r.text}"
    assert "cases" in r.json().get("detail", "").lower()


# ─── Username change permission guard ─────────────────────────────────────────


def test_super_admin_can_change_username() -> None:
    """Super admin can rename a user via PATCH /user/{username}; username is updated in DB."""
    s_super = _session()
    _login(s_super, "superadmin@kanapi.dev", "super123")

    original = _create_user(s_super)
    original_username = original["username"]
    new_username = f"{original_username}_renamed"

    try:
        r = s_super.patch(f"{BASE}/user/{original_username}", json={"username": new_username})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert r.json()["username"] == new_username, "Username was not updated in the response"

        # Confirm the new username is fetchable and old one is gone
        r_new = s_super.get(f"{BASE}/user/{new_username}")
        assert r_new.status_code == 200, "New username not fetchable after rename"
        r_old = s_super.get(f"{BASE}/user/{original_username}")
        assert r_old.status_code == 404, "Old username still exists after rename"
    finally:
        s_super.delete(f"{BASE}/user/{new_username}")


def test_company_admin_cannot_change_username() -> None:
    """Company admin PATCH succeeds but the username field is silently ignored."""
    s_super = _session()
    _login(s_super, "superadmin@kanapi.dev", "super123")

    s_admin = _session()
    admin = _login(s_admin, "admin@acme.dev", "acme123")

    # Create a sub-user under the company admin (must set parent_id explicitly)
    sub_username = f"tmp_{uuid.uuid4().hex[:8]}"
    r = s_super.post(f"{BASE}/user/create", json={
        "username": sub_username,
        "email": f"{sub_username}@test.dev",
        "password": "tmppass123",
        "is_admin": False,
        "parent_id": admin["username"],
    })
    assert r.status_code == 200, f"Sub-user creation failed: {r.text}"
    try:
        r = s_admin.patch(f"{BASE}/user/{sub_username}", json={"username": f"{sub_username}_hacked"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert r.json()["username"] == sub_username, "Username should be unchanged for company admin"
    finally:
        s_super.delete(f"{BASE}/user/{sub_username}")


def test_regular_user_cannot_change_any_username() -> None:
    """A regular (non-admin) user gets 403 when attempting to PATCH any user's username."""
    s_super = _session()
    _login(s_super, "superadmin@kanapi.dev", "super123")

    target = _create_user(s_super)
    target_username = target["username"]

    try:
        s_regular = _session()
        _login(s_regular, "test@acme.dev", "test123")
        r = s_regular.patch(f"{BASE}/user/{target_username}", json={"username": "hacked"})
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
    finally:
        s_super.delete(f"{BASE}/user/{target_username}")


# ─── Company case search/filter ───────────────────────────────────────────────


def test_company_admin_my_cases_filter_by_status() -> None:
    """GET /company/my-cases?status=open returns only open cases."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")
    all_cases = s.get(f"{BASE}/company/my-cases").json()
    if not all_cases:
        pytest.skip("No company cases available")

    filtered = s.get(f"{BASE}/company/my-cases", params={"status": "open"}).json()
    assert isinstance(filtered, list)
    assert all(c["status"] == "open" for c in filtered)
    assert len(filtered) <= len(all_cases)


def test_company_admin_my_cases_filter_by_q() -> None:
    """GET /company/my-cases?q=<customer> returns only matching cases."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")

    # Create a case with a unique customer name
    companies = s.get(f"{BASE}/company/").json()
    company_id = companies[0]["id"]
    unique_customer = f"SearchTest_{uuid.uuid4().hex[:8]}"
    case = _create_case(s, company_id, customer=unique_customer)

    try:
        filtered = s.get(f"{BASE}/company/my-cases", params={"q": unique_customer}).json()
        assert len(filtered) >= 1
        assert any(c["customer"] == unique_customer for c in filtered)

        # Searching for nonsense returns no results (or fewer)
        empty = s.get(f"{BASE}/company/my-cases", params={"q": "zzz_nonexistent_xyz"}).json()
        assert unique_customer not in [c["customer"] for c in empty]
    finally:
        s.delete(f"{BASE}/case/{case['id']}")


def test_company_admin_my_cases_filter_by_archived() -> None:
    """GET /company/my-cases?archived=false excludes archived cases."""
    s = _session()
    _login(s, "admin@acme.dev", "acme123")

    active_cases = s.get(f"{BASE}/company/my-cases", params={"archived": "false"}).json()
    assert isinstance(active_cases, list)
    assert all(c.get("archived") is not True for c in active_cases)


def test_super_admin_company_cases_filter_by_status() -> None:
    """GET /company/{id}/cases?status=open returns only open cases for super admin."""
    s = _session()
    _login(s, "superadmin@kanapi.dev", "super123")

    companies = s.get(f"{BASE}/company/").json()
    assert companies, "No companies found"
    company_id = companies[0]["id"]

    all_cases = s.get(f"{BASE}/company/{company_id}/cases").json()
    if not all_cases:
        pytest.skip("No cases for this company")

    filtered = s.get(f"{BASE}/company/{company_id}/cases", params={"status": "open"}).json()
    assert isinstance(filtered, list)
    assert all(c["status"] == "open" for c in filtered)
    assert len(filtered) <= len(all_cases)


def test_super_admin_company_cases_filter_by_q() -> None:
    """GET /company/{id}/cases?q=<term> returns only matching cases for super admin."""
    s = _session()
    _login(s, "superadmin@kanapi.dev", "super123")

    companies = s.get(f"{BASE}/company/").json()
    company_id = companies[0]["id"]

    all_cases = s.get(f"{BASE}/company/{company_id}/cases").json()
    if not all_cases:
        pytest.skip("No cases for this company")

    # Search by a known customer name from the results
    known_customer = all_cases[0]["customer"]
    filtered = s.get(f"{BASE}/company/{company_id}/cases", params={"q": known_customer}).json()
    assert len(filtered) >= 1
    assert all(
        known_customer.lower() in c["customer"].lower() or known_customer.lower() in c["responsible_person"].lower()
        for c in filtered
    )


def test_super_admin_company_cases_combined_filters() -> None:
    """GET /company/{id}/cases with q + status returns the intersection."""
    s = _session()
    _login(s, "superadmin@kanapi.dev", "super123")

    companies = s.get(f"{BASE}/company/").json()
    company_id = companies[0]["id"]

    all_cases = s.get(f"{BASE}/company/{company_id}/cases").json()
    if not all_cases:
        pytest.skip("No cases for this company")

    # Use a known customer + status combo
    target = all_cases[0]
    filtered = s.get(
        f"{BASE}/company/{company_id}/cases",
        params={"q": target["customer"], "status": target["status"]},
    ).json()
    assert len(filtered) >= 1
    for c in filtered:
        assert c["status"] == target["status"]


def test_company_admin_search_forbidden_for_regular_user() -> None:
    """Regular user gets 403 on GET /company/my-cases (requires company admin)."""
    s = _session()
    _login(s, "test@acme.dev", "test123")
    r = s.get(f"{BASE}/company/my-cases")
    assert r.status_code == 403


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
