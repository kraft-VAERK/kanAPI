"""Main FastAPI application module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from fastapi import FastAPI, Request

from .health.health import router as health_router
from .middleware.logging import log_requests
from .v1.case.case import router as api_v1_router
from .v1.customer import router as customer_router

if TYPE_CHECKING:
    from starlette.responses import Response

app = FastAPI(title="kanAPI", description="API for managing cases")
prefix = "/api/v1"
# Include routers
app.include_router(api_v1_router, prefix=prefix, tags=["v1"])
app.include_router(health_router, prefix=prefix, tags=["health"])
app.include_router(customer_router, prefix=prefix, tags=["customer"])
app.get("/", include_in_schema=False)(lambda: {"message": "Welcome to kanAPI!"})


@app.middleware("http")
async def logging_middleware(
    request: Request,
    call_next: Callable[[Request], Response],
) -> Response:
    """Middleware to log HTTP requests with timing information."""
    return await log_requests(request, call_next)
