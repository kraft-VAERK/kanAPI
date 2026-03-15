"""Main FastAPI application module."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI

# Import db package to ensure __init__.py gets executed
# from .db.create_tables import create_tables
from .db.database import create_tables
from .health.health import router as health_router
from .v1.auth.auth import router as auth_v1_router
from .v1.auth.fga import close_fga_client
from .v1.case.case import router as case_v1_router
from .v1.case.models import CaseActivityDB  # noqa: F401
from .v1.case.storage import ensure_bucket
from .v1.company import router as company_v1_router
from .v1.company.models import CompanyDB  # noqa: F401
from .v1.customer import router as customer_v1_rounter
from .v1.user import router as user_v1_router

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
