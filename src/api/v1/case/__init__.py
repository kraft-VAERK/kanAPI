"""API version 1 router configuration.

This module configures all routes for API version 1,
including case endpoints and any other v1 API resources.
"""

from fastapi import APIRouter

from .case import router as case_router

# Create a main v1 router
router = APIRouter()

# Include all sub-routers
router.include_router(case_router)
