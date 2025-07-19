"""Main FastAPI application module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from fastapi import FastAPI, Request

# Import db package to ensure __init__.py gets executed
# from .db.create_tables import create_tables
from .db.database import create_tables
from .health.health import router as health_router
from .middleware.logging import log_requests
from .v1.auth.auth import router as auth_v1_router
from .v1.case.case import router as case_v1_router
from .v1.customer import router as customer_v1_rounter
from .v1.user import router as user_v1_router

if TYPE_CHECKING:
    from starlette.responses import Response

app = FastAPI(title="kanAPI", description="API for managing cases")
prefix = "/api/v1"
# auxiliary routers
app.include_router(health_router, prefix=prefix, tags=["health"])
# v1 routers
app.include_router(auth_v1_router, prefix=prefix, tags=["v1", "auth"])
app.include_router(case_v1_router, prefix=prefix, tags=["v1", "case"])
app.include_router(customer_v1_rounter, prefix=prefix, tags=["v1", "customer"])
app.include_router(user_v1_router, prefix=prefix, tags=["v1", "user"])
app.get("/", include_in_schema=False)(lambda: {"message": "Welcome to kanAPI!"})

# Create database tables if they don't exist
create_tables()


@app.middleware("http")
async def logging_middleware(
    request: Request,
    call_next: Callable[[Request], Response],
) -> Response:
    """Middleware to log HTTP requests with timing information."""
    return await log_requests(request, call_next)
