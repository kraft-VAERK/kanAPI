# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make dev          # Sync dependencies via uv
make run          # Run backend + frontend dev server in background
make run-prod     # Run the app (production, 4 workers)
make db           # Start all Docker services: PostgreSQL, MinIO, OpenFGA (detached)
make seed         # Wipe and re-seed PostgreSQL with test users/cases/documents
make seed-fga     # Create OpenFGA store + write authorization model (writes to .env automatically)
make lint         # Run Ruff linter
make lint-fix     # Run Ruff linter with auto-fix
make test         # Run pytest (unit + integration, excludes live tests)
make frontend     # npm install + vite build → frontend/dist/
make clean        # Kill ports 8000/5173/9000/9001, stop Docker (removes volumes), remove venv and __pycache__
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
│   │   ├── pages/
│   │   │   ├── dashboard/   # Role-specific views + shared components
│   │   │   ├── Dashboard.jsx  # Thin auth wrapper; delegates to dashboard/ components
│   │   │   ├── Login.jsx
│   │   │   └── Register.jsx
│   │   ├── App.jsx  # BrowserRouter + Routes
│   │   └── index.css
│   ├── dist/        # Built output (served by FastAPI or Nginx)
│   └── vite.config.js
├── src/
│   └── api/         # FastAPI backend
│       ├── main.py
│       ├── db/      # database.py, seed.py, seed_fga.py, config.py
│       ├── health/  # health.py
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
| `username` | String | PK — also used as FK target by `cases.user_id`, `case_activities.user_id` |
| `email` | String | unique |
| `full_name` | String | nullable |
| `password` | String | bcrypt hashed |
| `is_active` | Boolean | default True |
| `is_admin` | Boolean | default False |
| `parent_id` | String | FK → users.username (self-referential), nullable |

> No `id` column — `username` is the primary key. `parent_id` stores the **username** (not a UUID) of the parent user.

**Role derivation** (from `is_admin` + `parent_id`):
- Super admin: `is_admin=True`, `parent_id=NULL`
- Company admin: `is_admin=True`, `parent_id=<super_admin.username>`
- Regular sub-user: `is_admin=False`, `parent_id=<company_admin.username>`

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
| `responsible_person` | String | required — display name |
| `responsible_user_id` | String | FK → users.username, nullable — actual assigned user |
| `status` | String | `open`, `pending`, `in_progress`, `closed` |
| `customer` | String | required — free-text name/org |
| `created_at` | DateTime(tz) | |
| `updated_at` | DateTime(tz) | nullable |
| `user_id` | String | FK → users.username — case creator |
| `company_id` | UUID | FK → companies.id |
| `archived` | Boolean | default False — soft-archive flag |

> `customer` is a plain string on cases, not an FK. The `CustomerDB` table exists separately and is not linked to cases.

### Case Activity (`case_activities` table)
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | uuid7, PK |
| `case_id` | UUID | FK → cases.id, CASCADE delete |
| `user_id` | String | FK → users.username, SET NULL on delete, nullable |
| `action` | String | e.g. `case_created`, `status_changed`, `responsible_changed` |
| `detail` | String | nullable — human-readable change summary (e.g. `open → closed`) |
| `created_at` | DateTime(tz) | |

Activity rows are written by `db_log_activity()`. Currently logged events: `case_created` (on create), `status_changed`, `responsible_changed`, `case_archived`, `case_unarchived` (on `PATCH`), `document_deleted` (on document delete).

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
| PATCH | `/case/{case_id}` | cookie | `editor` | Partial update; logs field changes |
| DELETE | `/case/{case_id}` | cookie | `deleter` | Delete a case + clean FGA tuples + MinIO docs |
| GET | `/case/{case_id}/activity` | cookie | `viewer` | Activity log for a case (oldest first) |
| GET | `/case/{case_id}/documents` | cookie | `viewer` | List MinIO documents for a case |
| GET | `/case/{case_id}/documents/{filename}` | cookie | `viewer` | Download a document (StreamingResponse) |
| DELETE | `/case/{case_id}/documents/{filename}` | cookie | `editor` | Delete a document + log activity |

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
| POST | `/user/create` | cookie (admin) | Create a user |
| GET | `/user/delete` | cookie (admin) | Delete a user (uses GET+body — legacy) |
| PATCH | `/user/{user_id}` | cookie (admin) | Update a user |
| DELETE | `/user/{user_id}` | cookie (admin) | Delete a user by ID |
| GET | `/user/{user_id}/cases` | cookie | Get cases for a user |
| GET | `/user/{user_id}` | cookie (admin) | Get a user by ID |
| GET | `/user/all` | cookie | List all users |

### Customer (`/customer`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/customer/create` | cookie | Create a customer |

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
- `write_tuple_safe(...)` — write, suppress duplicate errors only (logs and re-raises other failures)
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
- `delete_case_documents(case_id)` — deletes all objects under `cases/{case_id}/` (called on case delete)

Documents are uploaded only via seed (`make seed`) — no upload endpoint exists yet. Documents can be deleted via `DELETE /case/{case_id}/documents/{filename}`.

---

## Database

PostgreSQL 15 in Docker (port 5432, db=`postgres`, user/pass=`admin`). Config: `database.ini`.

Connection + `Base` in `src/api/db/database.py`. All ORM models must be imported before `create_tables()` (handled via imports in `main.py`).

> `CaseDB` uses proper `UUID` + `DateTime(timezone=True)` columns. Some older models still use `String` for booleans/timestamps — that is legacy, not a convention to follow for new code.

---

## Authentication

Cookie-based JWT (`session` httponly cookie, 60 min expiry). `JWT_SECRET_KEY` is **required** (no default — app refuses to start without it). `JWT_ALGORITHM` defaults to HS256. Cookie `secure` flag controlled by `COOKIE_SECURE` env var (set `true` in production).

- Primary auth dependency: `get_current_user_from_cookie` in `src/api/v1/auth/auth.py`
- Also available: `get_current_user` (Bearer token, for Swagger)
- Passwords: bcrypt via `User.hash_password()`
- Rate limiting: disabled by default (local dev). Set `AUTH_RATE_LIMIT` env var in production (e.g. `10/minute`) to enable via slowapi

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
| `/dashboard/profile` | `Dashboard` | Current user's profile |
| `/company/:companyId` | `Dashboard` | Super admin: company detail (cases tab) |
| `/company/:companyId/clients` | `Dashboard` | Super admin: clients tab |
| `/company/:companyId/clients/:customer` | `Dashboard` | Super admin: filtered client cases |
| `/company/:companyId/users` | `Dashboard` | Super admin: users for a company |
| `/user/:userId` | `Dashboard` | User profile view |
| `/case/:caseId` | `Dashboard` | Case detail page (any role) |
| `/case/:caseId/edit` | `Dashboard` | Case edit form (any role) |
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

**All roles:** `/case/:caseId` → `CaseDetailPage` — case fields + documents list + Delete (with confirm step) + Archive/Unarchive. `/case/:caseId/edit` → edit form (status, customer, responsible person)

### Frontend component structure

`Dashboard.jsx` is a thin auth wrapper: fetches `/auth/me`, then renders the appropriate role-specific component. All view logic lives in `frontend/src/pages/dashboard/`:

- `SuperAdminDashboard` — companies list + company drill-down (cases, clients, users tabs)
- `CompanyAdminDashboard` — cases, customers, users tabs for company admin
- `UserDashboard` — cases + customers tabs for regular users; includes `CaseSearchBar`
- `CaseDetailPage` — Detail/Edit tabs, activity timeline, documents, archive/unarchive, delete; uses `location.state?.case` first, fetches on direct URL load
- `ProfileView` — current user's own profile
- `UserProfileView` — admin view of another user's profile

**Shared components** (all in `frontend/src/pages/dashboard/`):
- `CasesTable` — Customer (clickable → customer URL), Responsible, Status, Created, arrow button (→ `/case/:id`)
- `CustomersTable` — Name, Case count (derived in memory)
- `DocumentsTable` — File, Size, Uploaded, Download button, Delete button (with confirm step)
- `ActivityTimeline` — ordered list of `case_activities` entries
- `CaseDetail` — read-only fields for a single case (Customer, Responsible, Status, Created, Updated)
- `CaseEditForm` — edit form for case fields (status, customer, responsible_person); navigates back with toast on save
- `CaseSearchBar` — filter/search input for cases
- `CreateCaseModal` — `POST /case/create`; props: `fixedCompanyId`, `fixedCustomer`, `users` (dropdown) or `currentUsername` (read-only)
- `CreateCompanyModal` — `POST /company/`; optional owner dropdown
- `Pagination` — hides when ≤1 page, 10 items/page (`PAGE_SIZE = 10`)
- `constants.js` — `API` base URL, `PAGE_SIZE`
- `utils.js` — shared utility functions

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
- Use `_get_case_db_or_404(db, case_id)` to fetch the raw `CaseDB` row before mutating; it raises 404 automatically
- When you need the current user's identity in an endpoint that also uses `require_permission`, use `current_user: Annotated[User, Depends(require_permission(...))]` instead of `_auth` so the user object is accessible for logging

**Activity logging** — call `db_log_activity(db, case_id, user_id, action, detail=None)` after mutating state. Actions are free-form strings; keep them snake_case.

**DB functions available but not yet wired as endpoints:**
- `db_get_cases(db, skip, limit)` — paginated list of all cases (no FGA filter)
- `db_get_cases_by_responsible_user(db, user_id)` — cases where `responsible_user_id` matches

<!-- rtk-instructions v2 -->
# RTK (Rust Token Killer) - Token-Optimized Commands

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:
```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```

## RTK Commands by Workflow

### Build & Compile (80-90% savings)
```bash
rtk cargo build         # Cargo build output
rtk cargo check         # Cargo check output
rtk cargo clippy        # Clippy warnings grouped by file (80%)
rtk tsc                 # TypeScript errors grouped by file/code (83%)
rtk lint                # ESLint/Biome violations grouped (84%)
rtk prettier --check    # Files needing format only (70%)
rtk next build          # Next.js build with route metrics (87%)
```

### Test (90-99% savings)
```bash
rtk cargo test          # Cargo test failures only (90%)
rtk vitest run          # Vitest failures only (99.5%)
rtk playwright test     # Playwright failures only (94%)
rtk test <cmd>          # Generic test wrapper - failures only
```

### Git (59-80% savings)
```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)
```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```

### JavaScript/TypeScript Tooling (70-90% savings)
```bash
rtk pnpm list           # Compact dependency tree (70%)
rtk pnpm outdated       # Compact outdated packages (80%)
rtk pnpm install        # Compact install output (90%)
rtk npm run <script>    # Compact npm script output
rtk npx <cmd>           # Compact npx command output
rtk prisma              # Prisma without ASCII art (88%)
```

### Files & Search (60-75% savings)
```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%)
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)
```bash
rtk err <cmd>           # Filter errors only from any command
rtk log <file>          # Deduplicated logs with counts
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk summary <cmd>       # Smart summary of command output
rtk diff                # Ultra-compact diffs
```

### Infrastructure (85% savings)
```bash
rtk docker ps           # Compact container list
rtk docker images       # Compact image list
rtk docker logs <c>     # Deduplicated logs
rtk kubectl get         # Compact resource list
rtk kubectl logs        # Deduplicated pod logs
```

### Network (65-70% savings)
```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

### Meta Commands
```bash
rtk gain                # View token savings statistics
rtk gain --history      # View command history with savings
rtk discover            # Analyze Claude Code sessions for missed RTK usage
rtk proxy <cmd>         # Run command without filtering (for debugging)
rtk init                # Add RTK instructions to CLAUDE.md
rtk init --global       # Add RTK to ~/.claude/CLAUDE.md
```

## Token Savings Overview

| Category | Commands | Typical Savings |
|----------|----------|-----------------|
| Tests | vitest, playwright, cargo test | 90-99% |
| Build | next, tsc, lint, prettier | 70-87% |
| Git | status, log, diff, add, commit | 59-80% |
| GitHub | gh pr, gh run, gh issue | 26-87% |
| Package Managers | pnpm, npm, npx | 70-90% |
| Files | ls, read, grep, find | 60-75% |
| Infrastructure | docker, kubectl | 85% |
| Network | curl, wget | 65-70% |

Overall average: **60-90% token reduction** on common development operations.
<!-- /rtk-instructions -->