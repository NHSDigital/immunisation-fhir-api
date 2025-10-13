"""Data input model for DynamoDB"""

from typing import Optional

from fhir_api.models.fhir_r4.fhir_datatype_fields import FhirR4Fields
from pydantic import (
    BaseModel,
)


class DataInput(BaseModel):
    """Data input model"""

    nhsNumber: str = FhirR4Fields.string
    data: Optional[dict]


class SuccessModel(BaseModel):
    """SuccessModel for interacting with DynamoDB"""

    success: bool = FhirR4Fields.boolean
