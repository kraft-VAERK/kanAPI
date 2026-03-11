"""Main FastAPI application module."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Callable

import structlog
from fastapi import FastAPI, Request

# Import db package to ensure __init__.py gets executed
# from .db.create_tables import create_tables
from .db.database import create_tables
from .health.health import router as health_router
from .middleware.logging import log_requests
from .v1.auth.auth import router as auth_v1_router
from .v1.auth.fga import close_fga_client
from .v1.case.case import router as case_v1_router
from .v1.case.storage import ensure_bucket
from .v1.company import router as company_v1_router
from .v1.company.models import CompanyDB  # noqa: F401
from .v1.customer import router as customer_v1_rounter
from .v1.user import router as user_v1_router

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from starlette.responses import Response

# ── Structlog configuration ─────────────────────────────────────────────
# Must run at module level (before uvicorn sets up its own loggers).

shared_processors: list = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.filter_by_level,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt='iso'),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.UnicodeDecoder(),
]

structlog.configure(
    processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

formatter = structlog.stdlib.ProcessorFormatter(
    processors=[
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.processors.JSONRenderer(),
    ],
)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)

# Reconfigure the root logger
root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

# Intercept uvicorn's loggers so they also emit JSON
for name in ('uvicorn', 'uvicorn.access', 'uvicorn.error'):
    uv_logger = logging.getLogger(name)
    uv_logger.handlers.clear()
    uv_logger.propagate = True


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


@app.middleware("http")
async def logging_middleware(
    request: Request,
    call_next: Callable[[Request], Response],
) -> Response:
    """Middleware to log HTTP requests with timing information."""
    return await log_requests(request, call_next)
