from typing import List, Optional
from pydantic import BaseModel


class Coding(BaseModel):
    system: Optional[str] = None
    code: Optional[str] = None


class Details(BaseModel):
    coding: List[Coding]


class Issue(BaseModel):
    severity: Optional[str] = None
    code: Optional[str] = None
    details: Optional[Details] = None
    diagnostics: Optional[str] = None


class Meta(BaseModel):
    profile: List[str]


class OperationOutcome(BaseModel):
    resourceType: str
    id: Optional[str] = None
    meta: Optional[Meta] = None
    issue: List[Issue]
