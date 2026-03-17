from typing import Literal

from pydantic import BaseModel


class Coding(BaseModel):
    system: str | None = None
    code: str | None = None


class Details(BaseModel):
    coding: list[Coding]


class Issue(BaseModel):
    severity: str | None = None
    code: str | None = None
    details: Details | None = None
    diagnostics: str | None = None


class Meta(BaseModel):
    profile: list[str]


class OperationOutcome(BaseModel):
    resourceType: Literal["OperationOutcome"]
    id: str | None = None
    meta: Meta | None = None
    issue: list[Issue]
