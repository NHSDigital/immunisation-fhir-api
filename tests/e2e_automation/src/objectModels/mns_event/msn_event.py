from pydantic import BaseModel


class Filtering(BaseModel):
    generalpractitioner: str | None
    sourceorganisation: str | None
    sourceapplication: str
    subjectage: int
    immunisationtype: str
    action: str


class MnsEvent(BaseModel):
    specversion: str
    id: str
    source: str
    type: str
    time: str
    subject: str
    dataref: str
    filtering: Filtering | None = None
