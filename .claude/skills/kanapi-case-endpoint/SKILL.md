---
name: kanapi-case-endpoint
description: Adding new endpoints to the kanAPI case module. Activate when creating, modifying, or extending case API routes in this FastAPI project.
---

# kanAPI — Case Endpoint Pattern

Follow this pattern when adding or modifying endpoints in `src/api/v1/case/`.

## File Responsibilities

- **`models.py`** — SQLAlchemy ORM (`CaseDB`), Pydantic models, and all `db_*` database functions
- **`case.py`** — FastAPI router with endpoint handlers only; no DB logic here

## Step 1: Add DB function to `models.py`

```python
def db_<action>_case(db: Session, ...) -> Optional[Case]:
    """Docstring."""
    try:
        # SQLAlchemy logic
        db.commit()
        db.refresh(db_case)
        return Case(
            id=db_case.id,
            responsible_person=db_case.responsible_person,
            status=db_case.status,
            customer=db_case.customer,
            created_at=db_case.created_at,
            updated_at=db_case.updated_at,
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e!s}") from e
```

Always construct and return a `Case` Pydantic model (not the `CaseDB` ORM object).

## Step 2: Add endpoint to `case.py`

```python
@router.patch(
    "/{case_id}",
    response_model=Case,
    status_code=http.HTTPStatus.OK,
    summary="Short summary",
)
async def update_case(
    case_id: str,
    case: CaseUpdate,
    db: Session = db_dependency,
    current_user: User = Depends(get_current_user_from_cookie),
) -> Case:
    """Docstring."""
    result = db_update_case(db=db, case_id=case_id, case_update=case)
    if not result:
        raise HTTPException(
            status_code=http.HTTPStatus.NOT_FOUND,
            detail="Case not found.",
        )
    return result
```

## Auth

- Read endpoints (`GET`) — no auth required (currently)
- Write endpoints (`POST`, `PATCH`, `DELETE`) — require `current_user: User = Depends(get_current_user_from_cookie)`

## Conventions

- Use `http.HTTPStatus` constants, not raw integers
- Validate required fields explicitly and raise `400` before hitting the DB
- `case_id` is a UUID string generated with `str(uuid.uuid4())` at the endpoint layer
- `created_at` / `updated_at` are ISO 8601 strings: `datetime.now().isoformat()`
- The `db_dependency` shorthand (`Depends(get_db_session)`) is already defined at module level — reuse it

## Currently Implemented

| Method | Path | Auth | Handler |
|--------|------|------|---------|
| GET | `/api/v1/case/{case_id}` | No | `get_case` |
| POST | `/api/v1/case/create` | Yes | `create_case` |

DB functions available but not yet wired up: `db_get_cases`, `db_update_case`

## Database Notes

- DB runs in Docker via `make db`; config in `database.ini` (localhost:5432, db=postgres, user/pass=admin)
- Tables are auto-created on app startup via `create_tables()` in `main.py` — no migration step needed for schema changes during dev, but be aware that column type changes require manual ALTER or a drop/recreate
- All columns currently use `String` (including dates and booleans) — follow this convention for consistency unless doing a deliberate schema upgrade
- See the `postgres-patterns` skill for indexing and query optimization guidance
