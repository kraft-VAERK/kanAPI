# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make dev          # Create venv and install dependencies
make run          # Run backend + frontend dev server in background (logs/backend.log, logs/frontend.log)
make run-prod     # Run the app (production, 4 workers)
make db           # Start all Docker services: PostgreSQL, MinIO, OpenFGA (detached)
make seed         # Wipe and re-seed PostgreSQL with test users/cases/documents
make seed-fga     # Create OpenFGA store + write authorization model (writes to .env automatically)
make lint         # Run Ruff linter
make lint-fix     # Run Ruff linter with auto-fix
make test         # Run pytest (unit + integration, excludes live tests)
make frontend     # npm install + vite build → frontend/dist/
make clean        # Kill ports 8000/5173, remove venv and __pycache__
```

Run a single test:
```bash
uv run pytest tests/path/to/test.py::test_name -v
```

Run live integration tests (requires full stack):
```bash
uv run pytest tests/test_live.py -v
```

Frontend dev server (proxies /api to localhost:8000):
```bash
cd frontend && npm run dev
```

### First-time setup

```bash
make dev          # install deps
make db           # start docker services
make seed-fga     # creates FGA store + model, writes FGA_API_URL/FGA_STORE_ID/FGA_MODEL_ID to .env
make seed         # populate DB with test data
make run          # start backend + frontend
```

### Seeded credentials (after `make seed`)

| Email | Password | Role |
|-------|----------|------|
| `superadmin@kanapi.dev` | `super123` | Super admin |
| `admin@acme.dev` | `acme123` | Company admin (Acme) |
| `admin@globex.dev` | `globex123` | Company admin (Globex) |
| `test@acme.dev` | `test123` | Regular user (Acme) |

Sub-users are Faker-generated (5 per company admin). Passwords follow `<username>123`.

---

## Architecture

FastAPI app at `src/api/main.py`. All routes under `/api/v1`. Startup calls `create_tables()` and `ensure_bucket()`.

**Project layout:**
```
kanAPI/
├── frontend/        # React/Vite SPA
│   ├── src/
│   │   ├── pages/   # Login.jsx, Register.jsx, Dashboard.jsx
│   │   ├── App.jsx  # BrowserRouter + Routes
│   │   └── index.css
│   ├── dist/        # Built output (served by FastAPI or Nginx)
│   └── vite.config.js
├── src/
│   └── api/         # FastAPI backend
│       ├── main.py
│       ├── db/      # database.py, seed.py, seed_fga.py, config.py
│       ├── health/  # health.py
│       ├── middleware/
│       └── v1/      # case/, customer/, user/, auth/, company/
└── tests/
```

**Module layout** — each domain lives in `src/api/v1/<domain>/`:
- `models.py` — SQLAlchemy ORM model (`*DB` class), Pydantic models, `db_*` functions
- `<domain>.py` — FastAPI router (endpoint handlers only, no DB logic)

---

## Data Models

### User (`users` table)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | uuid7, PK |
| `username` | String | unique |
| `email` | String | unique |
| `full_name` | String | nullable |
| `password` | String | SHA-256 hashed |
| `is_active` | Boolean | default True |
| `is_admin` | Boolean | default False |
| `parent_id` | UUID | FK → users.id (self-referential), nullable |

**Role derivation** (from `is_admin` + `parent_id`):
- Super admin: `is_admin=True`, `parent_id=NULL`
- Company admin: `is_admin=True`, `parent_id=<super_admin.id>`
- Regular sub-user: `is_admin=False`, `parent_id=<company_admin.id>`

### Company (`companies` table)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | uuid7, PK |
| `name` | String | required |
| `email` | String | nullable |
| `phone` | String | nullable |
| `address` | String | nullable |
| `owner_id` | UUID | FK → companies.id (self-referential, nullable) — parent/owner company |
| `created_at` | DateTime(tz) | |

Owner companies have `owner_id=NULL`. Client companies point to their parent with `owner_id`.

### Case (`cases` table)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | uuid7, PK |
| `responsible_person` | String | required |
| `status` | String | `open`, `pending`, `in_progress`, `closed` |
| `customer` | String | required — free-text name/org |
| `created_at` | DateTime(tz) | |
| `updated_at` | DateTime(tz) | nullable |
| `user_id` | UUID | FK → users.id |
| `company_id` | UUID | FK → companies.id |

> `customer` is a plain string on cases, not an FK. The `CustomerDB` table exists separately and is not linked to cases.

### Customer (`customers` table)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | uuid7, PK |
| `name` | String | required |
| `email` | String | unique, required |
| `phone` | String | nullable |
| `address` | String | nullable |

---

## Full API Endpoint Reference

All endpoints under `/api/v1`.

### Auth (`/auth`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/login` | — | JSON `{email, password}`, sets `session` cookie |
| POST | `/auth/token` | — | OAuth2 form (Swagger UI), sets cookie |
| POST | `/auth/logout` | — | Clears `session` cookie |
| GET | `/auth/me` | cookie | Returns current user |

### Case (`/case`)
| Method | Path | Auth | FGA | Description |
|--------|------|------|-----|-------------|
| GET | `/case/` | cookie | batch_check `viewer` | All cases for current user (FGA filtered) |
| GET | `/case/{case_id}` | cookie | `viewer` | Get a single case |
| POST | `/case/create` | cookie | writes `creator` + `company` tuples | Create a case |
| DELETE | `/case/{case_id}` | cookie | `deleter` | Delete a case + clean FGA tuples |
| GET | `/case/{case_id}/documents` | cookie | `viewer` | List MinIO documents for a case |
| GET | `/case/{case_id}/documents/{filename}` | cookie | `viewer` | Download a document (StreamingResponse) |

### Company (`/company`)
| Method | Path | Auth | Access | Description |
|--------|------|------|--------|-------------|
| GET | `/company/` | cookie | any authenticated | List all companies |
| POST | `/company/` | cookie | super admin | Create a company |
| GET | `/company/my-users` | cookie | company admin | Sub-users under this admin |
| GET | `/company/mine` | cookie | company admin | Companies derived from sub-users' cases |
| GET | `/company/my-cases` | cookie | company admin | All cases across sub-users |
| GET | `/company/{company_id}/clients` | cookie | super admin | Client companies owned by this company |
| GET | `/company/{company_id}/users` | cookie | super admin | Sub-users belonging to a company |
| GET | `/company/{company_id}/cases` | cookie | super admin | Cases for company + its clients |

### User (`/user`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/user/create` | — | Create a user (no auth guard) |
| GET | `/user/delete` | — | Delete a user (no auth guard, uses GET+body — legacy) |
| GET | `/user/all` | cookie | List all users |

### Customer (`/customer`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/customer/create` | — | Create a customer (no auth guard) |

### Health (`/health`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health/startup` | Startup probe |
| GET | `/health/ready` | Readiness probe |
| GET | `/health/live` | Liveness probe |

---

## Authorization — OpenFGA

OpenFGA runs in Docker (port 8080, playground at 3000). Required env vars: `FGA_API_URL`, `FGA_STORE_ID`, `FGA_MODEL_ID` — written to `.env` by `make seed-fga`.

**Types:**
- `user` — a human user
- `company` — has `member` and `admin` relations (both direct `user`)
- `case` — has `company`, `creator`, `assignee`, `viewer`, `editor`, `deleter`

**Computed relations on `case`:**
- `viewer` = direct ∪ `editor` ∪ `creator` ∪ `assignee` ∪ company's `admin` (via `company` relation)
- `editor` = direct ∪ `creator`
- `deleter` = direct ∪ `creator` ∪ company's `admin` (via `company` relation)

> Company admins are computed `viewer` (and `deleter`) on all cases belonging to their company via `tupleToUserset`. This means company admins can call `GET /case/{id}`, `GET /case/{id}/documents`, and `DELETE /case/{id}` on sub-user cases without any extra tuples.

**Written on case create:**
1. `user:<user_id> creator case:<case_id>`
2. `company:<company_id> company case:<case_id>`
3. If creator has a parent admin: `user:<parent_id> admin company:<company_id>` (idempotent via `write_tuple_safe`)

**Deleted on case delete:** `creator` tuple + `company` tuple.

**FGA helpers (`src/api/v1/auth/fga.py`):**
- `check_permission(user_id, relation, object_type, object_id)` → bool
- `write_tuple(subject_id, relation, object_type, object_id, subject_type='user')`
- `delete_tuple(...)` — same signature
- `write_tuple_safe(...)` — write, silently ignore duplicate errors
- `filter_by_permission(cases, user_id, relation='viewer')` — batch_check filter
- `require_permission(relation, object_type='case')` — FastAPI dependency factory (raises 403)

---

## Document Storage — MinIO

MinIO runs in Docker (port 9000, console at 9001). Credentials: `minioadmin` / `minioadmin`. Bucket: `kanapi`.

Object path: `cases/{case_id}/{filename}`

Helpers in `src/api/v1/case/storage.py`:
- `ensure_bucket()` — called at startup
- `list_case_documents(case_id)` → `list[{name, size, last_modified}]`
- `stream_case_document(case_id, filename)` → `(HTTPResponse, content_type)`

Documents are uploaded only via seed (`make seed`) — no upload endpoint exists yet.

---

## Database

PostgreSQL 15 in Docker (port 5432, db=`postgres`, user/pass=`admin`). Config: `database.ini`.

Connection + `Base` in `src/api/db/database.py`. All ORM models must be imported before `create_tables()` (handled via imports in `main.py`).

> `CaseDB` uses proper `UUID` + `DateTime(timezone=True)` columns. Some older models still use `String` for booleans/timestamps — that is legacy, not a convention to follow for new code.

---

## Authentication

Cookie-based JWT (`session` httponly cookie, 60 min expiry). `JWT_SECRET_KEY` + `JWT_ALGORITHM` from env (default: HS256).

- Primary auth dependency: `get_current_user_from_cookie` in `src/api/v1/auth/auth.py`
- Also available: `get_current_user` (Bearer token, for Swagger)
- Passwords: SHA-256 via `User.hash_password()`

---

## Frontend (React/Vite SPA)

Built output at `frontend/dist/`. Dev server proxies `/api` → `localhost:8000`.

### URL routing (`frontend/src/App.jsx`)

All navigation is URL-based — no pure React state routing. React Router v6.

| Path | Component | Notes |
|------|-----------|-------|
| `/` | `Login` | |
| `/register` | `Register` | |
| `/dashboard` | `Dashboard` | Company admin / regular user default view |
| `/dashboard/customers` | `Dashboard` | Customers tab |
| `/dashboard/customers/:customer` | `Dashboard` | Filtered cases for a customer |
| `/dashboard/users` | `Dashboard` | Users tab (company admin only) |
| `/company/:companyId` | `Dashboard` | Super admin: company detail (cases tab) |
| `/company/:companyId/clients` | `Dashboard` | Super admin: clients tab |
| `/company/:companyId/clients/:customer` | `Dashboard` | Super admin: filtered client cases |
| `/case/:caseId` | `Dashboard` | Case detail page (any role) |
| `*` | redirect → `/` | |

Customer names in URLs are `encodeURIComponent`-encoded on navigate and `decodeURIComponent`-decoded on read.

Case navigation: `navigate(\`/case/${c.id}\`, { state: { case: c } })` — passes case object via router state to avoid an extra API call. Falls back to `GET /case/{id}` for direct URL access (works for users with FGA `creator` tuple; super admin / company admin must navigate from a table).

### Dashboard views by role

**Super admin** (`is_admin=True`, `parent_id=null`):
- `/` (default) → companies list (`CompaniesListView`), paginated 10/page + "+ Add Company" modal
- `/company/:companyId` → `CompanyDetailView` with tabs:
  - **Cases** (`GET /company/{id}/cases`) — all cases for company + clients
  - **Clients** (`GET /company/{id}/clients`) — customer list; click → `/company/:id/clients/:customer`
- `/company/:companyId/clients/:customer` → filtered cases for that client + "+ Add Case" modal

**Company admin** (`is_admin=True`, `parent_id!=null`):
- `/dashboard` → Cases tab (`GET /company/my-cases`)
- `/dashboard/customers` → Customers tab (derived from case.customer in memory)
- `/dashboard/customers/:customer` → filtered cases + "+ Add Case" modal
- `/dashboard/users` → Users tab (`GET /company/my-users`)

**Regular user** (`is_admin=False`):
- `/dashboard` → Cases tab (`GET /case/`, FGA-filtered)
- `/dashboard/customers` → Customers tab (derived from case.customer in memory)
- `/dashboard/customers/:customer` → filtered cases + "+ New Case" modal

**All roles:** `/case/:caseId` → `CaseDetailPage` — case fields + documents list + Delete (with confirm step)

### Shared frontend components (all in `frontend/src/pages/Dashboard.jsx`)
- `CasesTable` — ID (clickable → `/case/:id`), Customer (clickable → customer URL), Responsible, Status, Created
- `CustomersTable` — Name, Case count (derived in memory)
- `DocumentsTable` — File, Size, Modified, Download button
- `CaseDetailPage` — uses `location.state?.case` first, fetches only on direct URL load
- `CreateCaseModal` — `POST /case/create`; props: `fixedCompanyId`, `fixedCustomer`, `users` (dropdown) or `currentUsername` (read-only)
- `CreateCompanyModal` — `POST /company/`; optional owner dropdown
- `Pagination` — hides when ≤1 page, 10 items/page (`PAGE_SIZE = 10`)

---

## Seeded Data Structure

After `make seed`:
- 1 super admin
- 2 company admins (Acme, Globex) with `parent_id=super_admin.id`
- 5 Faker-generated sub-users per company admin
- 5 companies: Acme Inc. + Globex Corp. (owner-level) + Springfield Legal + Burns & Associates (Acme clients) + Shelbyville Partners (Globex client)
- ~50-75 cases per company (5 fake customers × 10-15 cases each), assigned to sub-users and client companies
- 1-3 `.txt` documents per case in MinIO (report, notes, invoice, contract, evidence templates)
- FGA tuples: `creator` + `company` per case; `admin` per admin-company pair

---

## Code Style

Ruff is the linter (config in `pyproject.toml`). Line length: 120. Double quotes for docstrings, single quotes for inline strings.

---

## Adding a New Case Endpoint

**Step 1 — add a `db_*` function to `models.py`:**
```python
def db_<action>_case(db: Session, ...) -> Optional[Case]:
    try:
        # SQLAlchemy logic
        db.commit()
        db.refresh(db_case)
        return Case(id=db_case.id, ...)  # always return Pydantic, not ORM
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e!s}") from e
```

**Step 2 — wire it in `case.py`:**
```python
@router.patch("/{case_id}", response_model=Case, status_code=http.HTTPStatus.OK)
async def update_case(
    case_id: str,
    case: CaseUpdate,
    db: DbSession,
    _auth: Annotated[User, Depends(require_permission('editor'))],
) -> Case:
    result = db_update_case(db=db, case_id=case_id, case_update=case)
    if not result:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND, detail="Case not found.")
    return result
```

**Conventions:**
- Use `http.HTTPStatus` constants, not raw integers
- `case_id` = `str(uuid7())` at endpoint layer (UUID v7, time-ordered; from `uuid_extensions`)
- Timestamps = `datetime.now(timezone.utc)`
- Reuse `DbSession` and `CurrentUser` annotated dependencies defined at module level in `case.py`
- All case endpoints require authentication — no public endpoints on case routes
- Use `Depends(require_permission('<relation>'))` for FGA checks; call `await write_tuple(...)` after creating a resource

**DB functions available but not yet wired as endpoints:**
- `db_get_cases(db, skip, limit)` — paginated list of all cases (no FGA filter)
- `db_update_case(db, case_id, case_update)` — partial update via `CaseUpdate`
