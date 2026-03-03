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
make clean        # Remove venv and __pycache__
```

Run a single test:
```bash
. venv/bin/activate && PYTHONPATH=src pytest tests/path/to/test.py::test_name -v
```

## Architecture

FastAPI app at `src/api/main.py`. All routes are under `/api/v1`. The app calls `create_tables()` at startup to auto-create tables from SQLAlchemy models.

**Module layout** — each domain (`case`, `customer`, `user`, `auth`) lives in `src/api/v1/<domain>/` and has:
- `models.py` — SQLAlchemy ORM model (`*DB` class), Pydantic models, and `db_*` functions for database operations
- `<domain>.py` — FastAPI router with endpoint handlers

**Database** — PostgreSQL, configured via `database.ini`. Connection and `Base` are defined in `src/api/db/database.py`. All ORM models inherit from `Base` and must be imported before `create_tables()` runs (currently handled via imports in `main.py`).

**Authentication** — JWT-based, stored in an httponly session cookie. Two auth flows:
- `POST /api/v1/auth/login` — JSON body with email/password, sets `session` cookie
- `POST /api/v1/auth/token` — OAuth2 form-based (for Swagger UI)

Protected endpoints use `Depends(get_current_user_from_cookie)` from `src/api/v1/auth/auth.py`. Passwords are hashed with SHA-256 in `User.hash_password()`.

**Adding a new endpoint** — follow the case module pattern: add `db_*` functions to `models.py`, wire them in `<domain>.py` as router methods, then include the router in `main.py`.

## Code Style

Ruff is the linter (config in `pyproject.toml`). Line length: 120. Double quotes for docstrings, single quotes for inline strings.
