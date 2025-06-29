"""Logging middleware for the API."""

import logging
import time
from typing import Awaitable, Callable

from fastapi import Request
from starlette.responses import Response


async def log_requests(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Log HTTP requests with timing information.

    Args:
        request: The incoming request object
        call_next: The next middleware or endpoint handler in the chain

    Returns:
        The response from the next handler

    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logging.info(
        f"Endpoint: {request.method} {request.url.path} | "
        f"Status: {response.status_code} | "
        f"Time: {process_time:.4f}s",
    )
    return response
