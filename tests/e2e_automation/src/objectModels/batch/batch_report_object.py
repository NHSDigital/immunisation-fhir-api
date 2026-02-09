from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, validator


class IngestionTime(BaseModel):
    start: int
    end: int

    @validator("end")
    def validate_order(cls, v, values):
        start = values.get("start")
        if start is not None and v <= start:
            raise ValueError("ingestionTime.end must be greater than start")
        return v


class Summary(BaseModel):
    totalRecords: int
    succeeded: int
    failed: int
    ingestionTime: IngestionTime


class FailureDetail(BaseModel):
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
    failures: Optional[List[FailureDetail]]

    @validator("generatedDate")
    def validate_generated_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            raise ValueError("generatedDate must be ISO‑8601 format ending with 'Z'")
        return v
