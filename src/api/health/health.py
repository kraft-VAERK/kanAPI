"""Health check endpoints for the application."""

import http

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/startup", status_code=http.HTTPStatus.OK)
async def startup_health() -> http.HTTPStatus:
    """Health check for application startup."""
    return http.HTTPStatus.OK


@router.get("/ready", status_code=http.HTTPStatus.OK)
async def readiness_check() -> http.HTTPStatus:
    """Check if the application is ready to receive traffic."""
    return http.HTTPStatus.OK


@router.get("/live", status_code=http.HTTPStatus.OK)
async def liveness_check() -> http.HTTPStatus:
    """Check if the application is live."""
    return http.HTTPStatus.OK
