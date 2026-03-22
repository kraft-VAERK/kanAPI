"""Audit logging middleware — logs who did what to a rotating file.

Skips noisy/read-only endpoints (health checks, /auth/me, static files).
Decodes the user from the session JWT cookie when present.
"""

from __future__ import annotations

import json
import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING

import jwt
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from fastapi import Request, Response

# ── Logger setup ────────────────────────────────────────────────────────
_LOG_DIR = Path(__file__).resolve().parents[3] / 'logs'
_LOG_FILE = _LOG_DIR / 'audit.log'

audit_logger = logging.getLogger('kanapi.audit')
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False

def _get_secret() -> str:
    return os.getenv('JWT_SECRET_KEY', '')


def _get_algorithm() -> str:
    return os.getenv('JWT_ALGORITHM', 'HS256')

# Paths to skip — noisy or irrelevant
_SKIP_PATHS: set[str] = {
    '/api/v1/auth/me',
    '/api/v1/health/startup',
    '/api/v1/health/ready',
    '/api/v1/health/live',
}

# Also skip any path starting with these prefixes
_SKIP_PREFIXES: tuple[str, ...] = (
    '/assets/',
    '/favicon',
)

_LOGIN_PATHS: set[str] = {
    '/api/v1/auth/login',
    '/api/v1/auth/token',
}


def _setup_file_handler() -> None:
    """Attach a rotating file handler if not already present."""
    if audit_logger.handlers:
        return
    _LOG_DIR.mkdir(exist_ok=True)
    handler = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
    )
    handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    audit_logger.addHandler(handler)


def _extract_user(request: Request) -> str:
    """Try to decode username from the session cookie JWT."""
    token = request.cookies.get('session')
    if not token:
        return 'anonymous'
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=[_get_algorithm()])
        return payload.get('sub', 'unknown')
    except Exception:
        return 'invalid-token'


class AuditMiddleware(BaseHTTPMiddleware):
    """Log meaningful requests (mutations, auth) to audit.log."""

    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        """Process request and log audit entry."""
        path = request.url.path
        method = request.method

        # Skip noisy endpoints
        if path in _SKIP_PATHS or path.startswith(_SKIP_PREFIXES):
            return await call_next(request)

        # Log all methods — only _SKIP_PATHS and _SKIP_PREFIXES are excluded above

        _setup_file_handler()

        user = _extract_user(request)
        login_email = ''
        if path in _LOGIN_PATHS and method == 'POST':
            login_email = await self._extract_login_email(request)

        start = time.monotonic()

        response = await call_next(request)

        duration_ms = (time.monotonic() - start) * 1000
        client_ip = request.client.host if request.client else 'unknown'

        extra = f' (email={login_email})' if login_email else ''
        audit_logger.info(
            '%s | %s | %s %s%s | %d | %.0fms',
            user,
            client_ip,
            method,
            path,
            extra,
            response.status_code,
            duration_ms,
        )

        return response

    @staticmethod
    async def _extract_login_email(request: Request) -> str:
        """Read the email from a login request body (JSON or form)."""
        try:
            body = await request.body()
            content_type = request.headers.get('content-type', '')
            if 'json' in content_type:
                data = json.loads(body)
                return data.get('email', '')
            if 'form' in content_type:
                # OAuth2 form uses 'username' field (which holds the email)
                text = body.decode()
                for pair in text.split('&'):
                    key, _, value = pair.partition('=')
                    if key == 'username':
                        from urllib.parse import unquote_plus
                        return unquote_plus(value)
        except Exception:
            pass
        return ''
