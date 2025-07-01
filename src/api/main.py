"""Main FastAPI application module."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Callable

import uvicorn
from fastapi import FastAPI, Request
from middleware.logging import log_requests

from .health.health import router as health_router
from .v1.case.case import router as api_v1_router

if TYPE_CHECKING:
    from starlette.responses import Response

app = FastAPI()

app = FastAPI(title="kanAPI", description="API for managing cases")

# Include routers
app.include_router(api_v1_router, prefix="/api/v1", tags=["v1"])
app.include_router(health_router, prefix="/api/v1", tags=["health"])


@app.middleware("http")
async def logging_middleware(
    request: Request,
    call_next: Callable[[Request], Response],
) -> Response:
    """Middleware to log HTTP requests with timing information."""
    return await log_requests(request, call_next)


if __name__ == "__main__":
    logging.info("Starting FastAPI application...")
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "dev":
            # Run in watch mode for development
            uvicorn.run(
                "main:app",
                host="0.0.0.0",
                port=8000,
                log_level="warning",
                reload=True,
            )
        elif mode == "prod":
            # Run without watch mode for production
            uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
        else:
            logging.error(
                "Invalid mode specified",
            )
            sys.exit(1)
    else:
        logging.error(
            "No mode specified",
        )
        sys.exit(1)
