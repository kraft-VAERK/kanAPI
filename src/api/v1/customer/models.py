"""Customer model for API v1."""

import pydantic


class Customer(pydantic.BaseModel):  # noqa: D101
    id: int
    name: str
    email: str
    phone: str | None = None
    address: str | None = None
