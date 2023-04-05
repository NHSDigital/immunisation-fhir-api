''' Data input model for DynamoDB '''

from typing import Optional
from pydantic import (
    BaseModel,
)

from fhir_api.models.fhir_r4.fhir_datatype_fields import FhirR4Fields

class DataInput(BaseModel):
    ''' Data input model '''
    nhsNumber: str = FhirR4Fields.string
    data: Optional[dict]

class SuccessModel(BaseModel):
    ''' SuccessModel for interacting with DynamoDB'''
    success: bool = FhirR4Fields.boolean
