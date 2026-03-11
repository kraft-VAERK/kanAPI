"""Structured logging middleware for the API."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Awaitable, Callable

import jwt
import structlog

from src.api.v1.auth.auth import ALGORITHM, SECRET_KEY

if TYPE_CHECKING:
    from fastapi import Request
    from starlette.responses import Response

logger = structlog.stdlib.get_logger()


def _extract_user(request: Request) -> dict[str, str]:
    """Extract username and email from the session JWT cookie without a DB call."""
    session = request.cookies.get('session')
    if not session:
        return {'username': 'anonymous', 'email': ''}
    try:
        payload = jwt.decode(session, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            'username': payload.get('sub', 'anonymous'),
            'email': payload.get('email', ''),
        }
    except jwt.PyJWTError:
        return {'username': 'anonymous', 'email': ''}


async def log_requests(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Log HTTP requests with structured context: request_id, user, timing.

    Args:
        request: The incoming request object
        call_next: The next middleware or endpoint handler in the chain

    Returns:
        The response from the next handler

    """
    request_id = str(uuid.uuid4())
    user_info = _extract_user(request)

    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    response.headers['X-Request-ID'] = request_id

    logger.info(
        'http_request',
        request_id=request_id,
        username=user_info['username'],
        email=user_info['email'],
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )

    return response
