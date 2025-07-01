"""API endpoints for managing cases.

This module provides routes for retrieving case information,
including functions to get cases by ID and generate fake case data.
"""

import http

from faker import Faker
from fastapi import APIRouter, HTTPException

from .models import Case, CaseList

router = APIRouter(prefix="/case", tags=["case"])


@router.get(
    "/{case_id}",
    response_model=Case,
    status_code=http.HTTPStatus.OK,
    summary="Get a case by ID",
)
async def read_case(case_id: str) -> Case:  # noqa: D103
    case = await get_case_by_id(case_id)
    if case:
        return case
    else:
        raise HTTPException(status_code=404, detail=f"Case with id {case_id} not found")


@router.post(
    "/create",
    response_model=Case,
    status_code=http.HTTPStatus.CREATED,
    summary="Create a new case",
)
async def create_case(case: Case) -> Case:
    """Create a new case.

    Parameters
    ----------
    case : Case
        The case object to create.

    Returns
    -------
    Case
        The created case object.

    """
    cases.cases.append(case)
    return case


async def get_case_by_id(case_id: str) -> Case | None:
    """Retrieve a case by its ID.

    Parameters
    ----------
    case_id : str
        The unique identifier of the case to find.

    Returns
    -------
    Case or None
        The case object if found, None otherwise.

    """
    for case in cases:
        if case.id == case_id:
            return case
    return None


fake = Faker()

cases = CaseList(
    cases=[
        Case(
            id=str(i),
            deleted=fake.boolean(chance_of_getting_true=20),
            responsible_person=fake.name(),
            status=fake.random_element(elements=("open", "closed", "pending")),
            customer=fake.company(),
        )
        for i in range(1, 21)
    ],
)
