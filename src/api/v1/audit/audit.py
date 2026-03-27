"""Audit log endpoint — super admin only."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.v1.auth.auth import get_current_user_from_cookie
from src.api.v1.user.models import User

router = APIRouter(prefix="/audit")

_LOG_DIR = Path(__file__).resolve().parents[4] / "logs"
_LOG_FILE = _LOG_DIR / "audit.log"

# Matches: 2024-01-15 10:30:45 | username | 192.168.1.1 | POST /path... | 200 | 45ms
_LINE_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| "
    r"(?P<username>\S+) \| "
    r"(?P<ip>\S+) \| "
    r"(?P<method>[A-Z]+) (?P<path>\S+)[^|]*\| "
    r"(?P<status>\d{3}) \| "
    r"(?P<duration>[\d.]+)ms",
)


class AuditEntry(BaseModel):
    """A single parsed audit log entry."""

    timestamp: str
    username: str
    ip: str
    method: str
    path: str
    status_code: int
    duration_ms: float


CurrentUser = Annotated[User, Depends(get_current_user_from_cookie)]


def _parse_log_file(path: Path) -> list[AuditEntry]:
    """Parse all valid lines in a log file, newest-first (reversed)."""
    if not path.exists():
        return []
    entries = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            m = _LINE_RE.search(line.rstrip())
            if not m:
                continue
            entries.append(
                AuditEntry(
                    timestamp=m.group("timestamp"),
                    username=m.group("username"),
                    ip=m.group("ip"),
                    method=m.group("method"),
                    path=m.group("path"),
                    status_code=int(m.group("status")),
                    duration_ms=float(m.group("duration")),
                ),
            )
    entries.reverse()
    return entries


def _read_all_logs() -> list[AuditEntry]:
    """Read main log file then rotated backups (audit.log.1 … audit.log.5)."""
    entries = _parse_log_file(_LOG_FILE)
    for i in range(1, 6):
        entries.extend(_parse_log_file(_LOG_FILE.with_suffix(f".log.{i}")))
    return entries


@router.get("/logs", response_model=list[AuditEntry])
async def get_audit_logs(
    current_user: CurrentUser,
    user: Optional[str] = Query(default=None, description="Filter by username"),  # noqa
    limit: int = Query(default=100, le=1000),
) -> list[AuditEntry]:
    """Return parsed audit log entries. Super admin only."""
    if not current_user.is_admin or current_user.parent_id:
        raise HTTPException(status_code=403, detail="Super admin access required.")

    entries = _read_all_logs()

    if user:
        entries = [e for e in entries if e.username == user]

    return entries[:limit]
