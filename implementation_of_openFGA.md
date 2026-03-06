# OpenFGA Integration for kanAPI — Case Authorization

## Current State

Case authorization lives in `_authorize_case_access` in `src/api/v1/case/case.py` — a hardcoded role hierarchy (super admin → company admin → case owner/same company). This works but gets complex as you add more granular permissions.

OpenFGA replaces this with **relationship-based access control (ReBAC)**: instead of checking `is_admin` and `parent_id` chains in Python, you write relationship tuples and OpenFGA resolves permissions.

---

## 1. Run OpenFGA Alongside Existing PostgreSQL

Add to `docker-compose.yml`:

```yaml
openfga-db:
  image: postgres:17
  environment:
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: password
    POSTGRES_DB: openfga
  ports:
    - "5433:5432"
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 5s
    timeout: 5s
    retries: 5

openfga-migrate:
  image: openfga/openfga:latest
  depends_on:
    openfga-db:
      condition: service_healthy
  command: migrate
  environment:
    OPENFGA_DATASTORE_ENGINE: postgres
    OPENFGA_DATASTORE_URI: "postgres://postgres:password@openfga-db:5432/openfga?sslmode=disable"

openfga:
  image: openfga/openfga:latest
  depends_on:
    openfga-migrate:
      condition: service_completed_successfully
  ports:
    - "8080:8080"   # HTTP API
    - "3000:3000"   # Playground UI
  environment:
    OPENFGA_DATASTORE_ENGINE: postgres
    OPENFGA_DATASTORE_URI: "postgres://postgres:password@openfga-db:5432/openfga?sslmode=disable"
  command: run
```

Three services:
1. **openfga-db** — dedicated PostgreSQL for OpenFGA data (port 5433 to avoid conflict with your app DB on 5432)
2. **openfga-migrate** — runs schema migrations then exits
3. **openfga** — the authorization server (HTTP on 8080, Playground UI on 3000)

---

## 2. Authorization Model

This maps the current hierarchy into OpenFGA relations:

```
model
  schema 1.1

type user

type company
  relations
    define member: [user]
    define admin: [user]

type case
  relations
    define company: [company]
    define creator: [user]
    define assignee: [user]
    define viewer: [user, company#member] or editor or creator or assignee
    define editor: [user] or creator
    define deleter: [user] or creator
```

What this means:
- A **case** belongs to a **company** (via the `company` relation)
- A **case** has a `creator`, `assignee`, and explicit `viewer`/`editor`/`deleter` relations
- **viewer** = anyone explicitly granted viewer, OR any member of the associated company, OR any editor, OR the creator, OR the assignee
- **editor** = anyone explicitly granted editor, OR the creator
- **deleter** = anyone explicitly granted deleter, OR the creator

### JSON format (for the Python SDK)

```python
CASE_AUTH_MODEL = {
    "schema_version": "1.1",
    "type_definitions": [
        {"type": "user"},
        {
            "type": "company",
            "relations": {
                "member": {"this": {}},
                "admin": {"this": {}},
            },
            "metadata": {
                "relations": {
                    "member": {"directly_related_user_types": [{"type": "user"}]},
                    "admin": {"directly_related_user_types": [{"type": "user"}]},
                }
            },
        },
        {
            "type": "case",
            "relations": {
                "company": {"this": {}},
                "creator": {"this": {}},
                "assignee": {"this": {}},
                "viewer": {
                    "union": {
                        "child": [
                            {"this": {}},
                            {"computedUserset": {"relation": "editor"}},
                            {"computedUserset": {"relation": "creator"}},
                            {"computedUserset": {"relation": "assignee"}},
                        ]
                    }
                },
                "editor": {
                    "union": {
                        "child": [
                            {"this": {}},
                            {"computedUserset": {"relation": "creator"}},
                        ]
                    }
                },
                "deleter": {
                    "union": {
                        "child": [
                            {"this": {}},
                            {"computedUserset": {"relation": "creator"}},
                        ]
                    }
                },
            },
            "metadata": {
                "relations": {
                    "company": {"directly_related_user_types": [{"type": "company"}]},
                    "creator": {"directly_related_user_types": [{"type": "user"}]},
                    "assignee": {"directly_related_user_types": [{"type": "user"}]},
                    "viewer": {
                        "directly_related_user_types": [
                            {"type": "user"},
                            {"type": "company", "relation": "member"},
                        ]
                    },
                    "editor": {
                        "directly_related_user_types": [
                            {"type": "user"},
                            {"type": "company", "relation": "member"},
                        ]
                    },
                    "deleter": {"directly_related_user_types": [{"type": "user"}]},
                }
            },
        },
    ],
}
```

---

## 3. Install the SDK

```bash
pip install openfga-sdk
```

Add `openfga-sdk` to `requirements.txt`.

---

## 4. FGA Client Module — `src/api/v1/auth/fga.py`

```python
import os

from fastapi import Depends, HTTPException
import http
from openfga_sdk.client import ClientConfiguration, OpenFgaClient
from openfga_sdk.client.models import ClientCheckRequest, ClientWriteRequest, ClientTuple

from src.api.v1.auth.auth import get_current_user_from_cookie

_fga_client: OpenFgaClient | None = None


async def get_fga_client() -> OpenFgaClient:
    """Return a reusable OpenFGA client (singleton)."""
    global _fga_client
    if _fga_client is None:
        config = ClientConfiguration(
            api_url=os.environ.get('FGA_API_URL', 'http://localhost:8080'),
            store_id=os.environ.get('FGA_STORE_ID'),
            authorization_model_id=os.environ.get('FGA_MODEL_ID'),
        )
        _fga_client = OpenFgaClient(config)
    return _fga_client


async def close_fga_client():
    """Call on app shutdown to clean up the client."""
    global _fga_client
    if _fga_client is not None:
        await _fga_client.close()
        _fga_client = None


async def check_permission(user_id: str, relation: str, object_type: str, object_id: str) -> bool:
    """Check if user has the given relation to the object."""
    client = await get_fga_client()
    response = await client.check(ClientCheckRequest(
        user=f'user:{user_id}',
        relation=relation,
        object=f'{object_type}:{object_id}',
    ))
    return response.allowed


async def write_tuple(user_id: str, relation: str, object_type: str, object_id: str):
    """Write a relationship tuple (e.g., user:X creator case:Y)."""
    client = await get_fga_client()
    await client.write(ClientWriteRequest(writes=[
        ClientTuple(user=f'user:{user_id}', relation=relation, object=f'{object_type}:{object_id}'),
    ]))


async def delete_tuple(user_id: str, relation: str, object_type: str, object_id: str):
    """Delete a relationship tuple."""
    client = await get_fga_client()
    await client.write(ClientWriteRequest(deletes=[
        ClientTuple(user=f'user:{user_id}', relation=relation, object=f'{object_type}:{object_id}'),
    ]))


def require_permission(relation: str, object_type: str = 'case'):
    """
    FastAPI dependency factory that checks OpenFGA permissions.

    Usage:
        @router.get("/{case_id}")
        async def get_case(
            case_id: str,
            _auth=Depends(require_permission("viewer")),
            db: Session = db_dependency,
        ):
    """
    async def checker(case_id: str, current_user=Depends(get_current_user_from_cookie)):
        if not await check_permission(current_user.id, relation, object_type, case_id):
            raise HTTPException(
                status_code=http.HTTPStatus.FORBIDDEN,
                detail=f'You do not have {relation} access to this {object_type}.',
            )
        return current_user
    return checker
```

---

## 5. Register Lifecycle Events in `main.py`

```python
from contextlib import asynccontextmanager
from src.api.v1.auth.fga import close_fga_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield
    await close_fga_client()

app = FastAPI(lifespan=lifespan)
```

---

## 6. Use in Case Endpoints

Replace `_authorize_case_access` calls with OpenFGA dependencies in `src/api/v1/case/case.py`:

### Create — write the creator tuple

```python
from src.api.v1.auth.fga import require_permission, write_tuple

@router.post('/create', response_model=Case, status_code=http.HTTPStatus.CREATED)
async def create_case(
    case: CaseCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> Case:
    case_id = str(uuid7())
    result = db_create_case(db=db, case_id=case_id, case=case)
    if not result:
        raise HTTPException(status_code=500, detail='Failed to create case.')

    # Write the creator relationship to OpenFGA
    await write_tuple(current_user.id, 'creator', 'case', case_id)
    return result
```

### Read — check viewer permission

```python
@router.get('/{case_id}', response_model=Case, status_code=http.HTTPStatus.OK)
async def get_case(
    case_id: str,
    _auth=Depends(require_permission('viewer')),
    db: DbSession,
) -> Case:
    result = db_get_case(db=db, case_id=case_id)
    if not result:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND, detail='Case not found.')
    return result
```

### Update — check editor permission

```python
@router.patch('/{case_id}', response_model=Case, status_code=http.HTTPStatus.OK)
async def update_case(
    case_id: str,
    case: CaseUpdate,
    _auth=Depends(require_permission('editor')),
    db: DbSession,
) -> Case:
    result = db_update_case(db=db, case_id=case_id, case_update=case)
    if not result:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND, detail='Case not found.')
    return result
```

### Delete — check deleter permission

```python
@router.delete('/{case_id}', status_code=http.HTTPStatus.NO_CONTENT)
async def delete_case(
    case_id: str,
    _auth=Depends(require_permission('deleter')),
    db: DbSession,
):
    success = db_delete_case(db=db, case_id=case_id)
    if not success:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND, detail='Case not found.')
```

---

## 7. Bootstrap Script — `src/api/db/seed_fga.py`

Run once to create the OpenFGA store and write the authorization model:

```python
import asyncio
import os

from openfga_sdk.client import ClientConfiguration, OpenFgaClient
from openfga_sdk.models.create_store_request import CreateStoreRequest

CASE_AUTH_MODEL = { ... }  # The JSON model from section 2 above


async def bootstrap():
    config = ClientConfiguration(
        api_url=os.environ.get('FGA_API_URL', 'http://localhost:8080'),
    )
    async with OpenFgaClient(config) as client:
        # 1. Create store
        store = await client.create_store(CreateStoreRequest(name='kanAPI'))
        print(f'Store ID: {store.id}')

        # 2. Write authorization model
        client.set_store_id(store.id)
        model_response = await client.write_authorization_model(CASE_AUTH_MODEL)
        print(f'Model ID: {model_response.authorization_model_id}')

        print()
        print('Set these environment variables:')
        print(f'  export FGA_STORE_ID={store.id}')
        print(f'  export FGA_MODEL_ID={model_response.authorization_model_id}')


if __name__ == '__main__':
    asyncio.run(bootstrap())
```

Usage:
```bash
. venv/bin/activate && python src/api/db/seed_fga.py
```

---

## 8. Tuple Lifecycle — When to Write/Delete

| Event | Tuple written |
|-------|---------------|
| User creates a case | `user:X creator case:Y` |
| User assigned to a case | `user:X assignee case:Y` |
| User joins a company | `user:X member company:Z` |
| User made company admin | `user:X admin company:Z` |
| Case linked to company | `company:Z company case:Y` → enables `company#member` viewer access |
| User removed from case | Delete the relevant tuple |
| Case deleted | Delete all tuples for that case |

---

## 9. Environment Variables

| Variable | Example | Description |
|----------|---------|-------------|
| `FGA_API_URL` | `http://localhost:8080` | OpenFGA HTTP API endpoint |
| `FGA_STORE_ID` | `01J...` | Store ID from bootstrap script |
| `FGA_MODEL_ID` | `01J...` | Authorization model ID from bootstrap script |

---

## 10. Decisions to Make Before Implementing

1. **Migration strategy** — Run both systems in parallel during transition, or switch over all at once? Existing cases need tuples backfilled.

2. **Company membership** — When a user is created under a company admin (`parent_id`), write `company#member` tuples. This replaces the `parent_id` hierarchy checks.

3. **Super admin** — Model as a special relation on a global object (e.g., `user:X admin system:global`) and check that in the dependency, or keep the `is_admin` flag for super admin and only use OpenFGA for case-level permissions.

4. **Tuple cleanup** — When a case is deleted, all its tuples should be cleaned up. OpenFGA doesn't cascade — you need to delete them explicitly.

---

## References

- [OpenFGA Documentation](https://openfga.dev/docs)
- [OpenFGA Python SDK](https://github.com/openfga/python-sdk)
- [OpenFGA Docker Setup](https://openfga.dev/docs/getting-started/setup-openfga/docker)
- [OpenFGA Playground](http://localhost:3000) (after running Docker)
- [OpenFGA Modeling Guide](https://openfga.dev/docs/modeling/getting-started)
