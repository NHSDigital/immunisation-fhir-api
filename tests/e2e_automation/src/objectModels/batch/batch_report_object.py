from pydantic import BaseModel
from typing import List, Optional


class IngestionTime(BaseModel):
    start: str
    end: str


class Summary(BaseModel):
    totalRecords: int
    success: int
    failed: int
    ingestionTime: IngestionTime


class Failure(BaseModel):
    rowId: int
    responseCode: str
    responseDisplay: str
    severity: str
    localId: str
    operationOutcome: str


class BatchReport(BaseModel):
    system: str
    version: int
    generatedDate: str
    filename: str
    provider: str
    messageHeaderId: str
    summary: Summary
    failures: Optional[List[Failure]]