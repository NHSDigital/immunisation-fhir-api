"""Read Models for Dynamodb"""

from typing import (
    Union,
    Literal,
    Optional,
)
from pydantic import (
    BaseModel,
    Field,
)

from fhir_api.models.fhir_r4.fhir_datatype_fields import FhirR4Fields
from fhir_api.models.fhir_r4.immunization import Immunization
from fhir_api.models.fhir_r4.patient import Patient


class Resource(BaseModel):
    """Wrapper Model for returned resource"""

    fullUrl: str = FhirR4Fields.uri
    resource: Union[Immunization, Patient]
    search: Optional[dict] = {"mode": "match"}  # This looks to be api specific


class BatchImmunizationRead(BaseModel):
    """Model for Multiple records"""

    resourceType: Literal["Bundle"] = Field(default="Bundle")
    type: str = FhirR4Fields.string
    total: int = FhirR4Fields.integer
    entry: list[Resource]
