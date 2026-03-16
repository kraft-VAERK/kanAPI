"""OpenFGA authorization client and FastAPI dependency helpers."""

from __future__ import annotations

import http
import logging
import os
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException
from openfga_sdk.client import ClientConfiguration, OpenFgaClient
from openfga_sdk.client.models import (
    ClientBatchCheckItem,
    ClientBatchCheckRequest,
    ClientCheckRequest,
    ClientTuple,
    ClientWriteRequest,
)

from src.api.v1.auth.auth import get_current_user_from_cookie
from src.api.v1.user.models import User  # noqa #TC001

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable

_fga_client: OpenFgaClient | None = None


async def get_fga_client() -> OpenFgaClient:
    """Return a reusable OpenFGA client (singleton)."""
    global _fga_client
    if _fga_client is None:
        config = ClientConfiguration(
            api_url=os.environ.get("FGA_API_URL", "http://localhost:8080"),
            store_id=os.environ.get("FGA_STORE_ID"),
            authorization_model_id=os.environ.get("FGA_MODEL_ID"),
        )
        _fga_client = OpenFgaClient(config)
    return _fga_client


async def close_fga_client() -> None:
    """Close the FGA client on app shutdown."""
    global _fga_client
    if _fga_client is not None:
        await _fga_client.close()
        _fga_client = None


async def check_permission(user_id: str, relation: str, object_type: str, object_id: str) -> bool:
    """Return True if user has the given relation to the object."""
    client = await get_fga_client()
    response = await client.check(
        ClientCheckRequest(
            user=f"user:{user_id}",
            relation=relation,
            object=f"{object_type}:{object_id}",
        ),
    )
    return response.allowed


async def write_tuple(
    subject_id: str,
    relation: str,
    object_type: str,
    object_id: str,
    subject_type: str = "user",
) -> None:
    """Write a relationship tuple (e.g. user:X creator case:Y)."""
    client = await get_fga_client()
    await client.write(
        ClientWriteRequest(
            writes=[
                ClientTuple(
                    user=f"{subject_type}:{subject_id}",
                    relation=relation,
                    object=f"{object_type}:{object_id}",
                ),
            ],
        ),
    )


async def delete_tuple(
    subject_id: str,
    relation: str,
    object_type: str,
    object_id: str,
    subject_type: str = "user",
) -> None:
    """Delete a relationship tuple."""
    client = await get_fga_client()
    await client.write(
        ClientWriteRequest(
            deletes=[
                ClientTuple(
                    user=f"{subject_type}:{subject_id}",
                    relation=relation,
                    object=f"{object_type}:{object_id}",
                ),
            ],
        ),
    )


async def write_tuple_safe(
    subject_id: str,
    relation: str,
    object_type: str,
    object_id: str,
    subject_type: str = "user",
) -> None:
    """Write a relationship tuple, silently ignoring duplicate errors only."""
    try:
        await write_tuple(subject_id, relation, object_type, object_id, subject_type=subject_type)
    except Exception as e:
        err_msg = str(e).lower()
        if 'already exists' in err_msg or 'duplicate' in err_msg or 'cannot write' in err_msg:
            return
        logger.error("FGA write_tuple_safe failed: %s (subject=%s:%s, relation=%s, object=%s:%s)",
                      e, subject_type, subject_id, relation, object_type, object_id)
        raise


async def filter_by_permission(cases: list, user_id: str, relation: str = "viewer") -> list:
    """Filter a list of Case objects to those the user has the given relation to."""
    if not cases:
        return []
    client = await get_fga_client()
    checks = [
        ClientBatchCheckItem(
            user=f"user:{user_id}",
            relation=relation,
            object=f"case:{case.id}",
            correlation_id=case.id,
        )
        for case in cases
    ]
    response = await client.batch_check(ClientBatchCheckRequest(checks=checks))
    allowed_ids = {r.correlation_id for r in response.result if r.allowed}
    return [c for c in cases if c.id in allowed_ids]


def require_permission(relation: str, object_type: str = "case") -> Callable:
    """FastAPI dependency factory — raises 403 if user lacks the given relation."""

    async def checker(
        case_id: str,
        current_user: Annotated[User, Depends(get_current_user_from_cookie)],
    ) -> User:
        if not await check_permission(current_user.username, relation, object_type, case_id):
            raise HTTPException(
                status_code=http.HTTPStatus.FORBIDDEN,
                detail=f"You do not have {relation} access to this {object_type}.",
            )
        return current_user

    return checker
