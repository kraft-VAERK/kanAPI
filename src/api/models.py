from pydantic import BaseModel


class Case(BaseModel):
    """Represents a case in the system.

    Attributes
    ----------
    id : str
        Unique identifier for the case.
    deleted : bool
        Flag indicating if the case has been deleted.
    responsible_person : str
        Name of the person responsible for the case.
    status : str
        Current status of the case.
    customer : str
        Name of the customer associated with the case.

    """

    id: str
    deleted: bool
    responsible_person: str
    status: str
    customer: str


class CaseList(BaseModel):
    """Represents a collection of Case objects.

    Attributes
    ----------
    cases : list[Case]
        List of Case objects in the collection.

    Methods
    -------
    __iter__() -> Iterator[Case]
        Returns an iterator over the cases in the collection.
    __getitem__(item: int) -> Case
        Returns the case at the specified index.
    __len__() -> int
        Returns the number of cases in the collection.

    Notes
    -----
    This class is used to manage a list of cases,
    providing methods to iterate over them,
    access individual cases by index, and get the total count of cases.
    It is designed to be used with Pydantic for data validation and serialization.

    """

    cases: list[Case]

    def __iter__(self) -> iter:  # noqa: D105
        return iter(self.cases)

    def __getitem__(self, item: int) -> Case:  # noqa: D105
        return self.cases[item]

    def __len__(self) -> int:  # noqa: D105
        return len(self.cases)
