"""Main FastAPI application module."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=True)

# These imports must come after load_dotenv() so env vars are available.
from .db.database import create_tables  # noqa: E402
from .health.health import router as health_router  # noqa: E402
from .middleware.audit import AuditMiddleware  # noqa: E402
from .v1.auth.auth import limiter  # noqa: E402
from .v1.auth.auth import router as auth_v1_router  # noqa: E402
from .v1.auth.fga import close_fga_client  # noqa: E402
from .v1.case.case import router as case_v1_router  # noqa: E402
from .v1.case.models import CaseActivityDB  # noqa: E402, F401
from .v1.case.storage import ensure_bucket  # noqa: E402
from .v1.company import router as company_v1_router  # noqa: E402
from .v1.company.models import CompanyDB  # noqa: E402, F401
from .v1.customer import router as customer_v1_rounter  # noqa: E402
from .v1.user import router as user_v1_router  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup tasks before yielding, then cleanup on shutdown."""
    create_tables()
    ensure_bucket()
    yield
    await close_fga_client()


app = FastAPI(title="kanAPI", description="API for managing cases", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(AuditMiddleware)

_cors_origins = [o.strip() for o in os.environ.get('CORS_ORIGINS', 'http://localhost:5173').split(',') if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
    allow_headers=['Content-Type', 'Authorization'],
)

prefix = "/api/v1"
# auxiliary routers
app.include_router(health_router, prefix=prefix, tags=["health"])
# v1 routers
app.include_router(auth_v1_router, prefix=prefix, tags=["v1", "auth"])
app.include_router(case_v1_router, prefix=prefix, tags=["v1", "case"])
app.include_router(company_v1_router, prefix=prefix, tags=["v1", "company"])
app.include_router(customer_v1_rounter, prefix=prefix, tags=["v1", "customer"])
app.include_router(user_v1_router, prefix=prefix, tags=["v1", "user"])
app.get("/api", include_in_schema=False)(lambda: {"message": "Welcome to kanAPI!"})
