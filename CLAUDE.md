# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make dev          # Create venv and install dependencies
make run          # Run the app (dev, with --reload)
make run-prod     # Run the app (production, 4 workers)
make db           # Start PostgreSQL via docker compose (detached)
make lint         # Run Ruff linter
make lint-fix     # Run Ruff linter with auto-fix
make test         # Run pytest (sets PYTHONPATH=src)
make frontend     # npm install + vite build → frontend/dist/
make clean        # Remove venv and __pycache__
```

Run a single test:
```bash
. venv/bin/activate && PYTHONPATH=src pytest tests/path/to/test.py::test_name -v
```

Frontend dev server (proxies /api to localhost:8000):
```bash
cd frontend && npm run dev
```

## Architecture

FastAPI app at `src/api/main.py`. All routes are under `/api/v1`. The app calls `create_tables()` at startup to auto-create tables from SQLAlchemy models.

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
│       ├── db/
│       ├── health/
│       ├── middleware/
│       └── v1/      # case, customer, user, auth
└── tests/
```

**Module layout** — each domain (`case`, `customer`, `user`, `auth`) lives in `src/api/v1/<domain>/` and has:
- `models.py` — SQLAlchemy ORM model (`*DB` class), Pydantic models, and `db_*` functions for database operations
- `<domain>.py` — FastAPI router with endpoint handlers only (no DB logic)

**Database** — PostgreSQL, configured via `database.ini`. Connection and `Base` are defined in `src/api/db/database.py`. All ORM models inherit from `Base` and must be imported before `create_tables()` runs (currently handled via imports in `main.py`). All columns use `String` type (including timestamps and booleans) — project convention.

**Authentication** — JWT-based, stored in an httponly session cookie. Two auth flows:
- `POST /api/v1/auth/login` — JSON body with email/password, sets `session` cookie
- `POST /api/v1/auth/token` — OAuth2 form-based (for Swagger UI)

Protected endpoints use `Depends(get_current_user_from_cookie)` from `src/api/v1/auth/auth.py`. Passwords are hashed with SHA-256 in `User.hash_password()`.

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
    db: Session = db_dependency,
    current_user: User = Depends(get_current_user_from_cookie),
) -> Case:
    result = db_update_case(db=db, case_id=case_id, case_update=case)
    if not result:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND, detail="Case not found.")
    return result
```

**Conventions:**
- Use `http.HTTPStatus` constants, not raw integers
- `case_id` = `str(uuid7())` at endpoint layer (UUID v7, time-ordered; from `uuid_extensions`)
- Timestamps = `datetime.now().isoformat()`
- Reuse the `db_dependency` shorthand (`Depends(get_db_session)`) defined at module level
- All endpoints require `Depends(get_current_user_from_cookie)` — no public endpoints on case routes

**Currently implemented endpoints:**

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/v1/case/{case_id}` | No |
| POST | `/api/v1/case/create` | Yes |

DB functions available but not yet wired: `db_get_cases`, `db_update_case`

## Code Style

Ruff is the linter (config in `pyproject.toml`). Line length: 120. Double quotes for docstrings, single quotes for inline strings.
