from pydantic import BaseModel, validator
from datetime import datetime
from typing import List, Optional
class IngestionTime(BaseModel):
    start: str
    end: str

    @validator("start", "end")
    def validate_unix_timestamp(cls, v):
        # Ensure it's numeric
        if not v.isdigit():
            raise ValueError("ingestionTime values must be numeric strings")

        # Optional: ensure it's a valid Unix timestamp
        try:
            datetime.utcfromtimestamp(int(v))
        except Exception:
            raise ValueError("Invalid Unix timestamp")

        return v

    @validator("end")
    def validate_order(cls, v, values):
        start = values.get("start")
        if start and int(v) <= int(start):
            raise ValueError("ingestionTime.end must be greater than start")
        return v


class Summary(BaseModel):
    totalRecords: int
    success: int
    failed: int
    ingestionTime: IngestionTime


class BatchReport(BaseModel):
    system: str
    version: int
    generatedDate: str
    filename: str
    provider: str
    messageHeaderId: str
    summary: Summary
    failures: Optional[List]

    @validator("generatedDate")
    def validate_generated_date(cls, v):
        try:
            # Enforce ISO‑8601 with Z suffix
            datetime.strptime(v, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            raise ValueError("generatedDate must be ISO‑8601 format ending with 'Z'")
        return v