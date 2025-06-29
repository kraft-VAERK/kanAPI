from pydantic import BaseModel

class Case(BaseModel):
    id: str
    deleted: bool
    responsible_person: str
    status: str
    customer: str


class CaseList(BaseModel):
    cases: list[Case]

    def __iter__(self):
        return iter(self.cases)

    def __getitem__(self, item):
        return self.cases[item]

    def __len__(self):
        return len(self.cases)
