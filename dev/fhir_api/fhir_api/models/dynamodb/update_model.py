''' Update Model for Immunization Records '''

import datetime

from typing import Optional, Literal, Any
from pydantic import BaseModel, Field

import fhir_api.models.fhir_r4.code_types as code_types
from fhir_api.models.fhir_r4.fhir_datatype_fields import FhirR4Fields
from fhir_api.models.fhir_r4.common import (
    CodeableConceptType,
    Reference,
    Quantity,
)

from fhir_api.models.fhir_r4.immunization import (
    Performer,
    ProtocolApplied,
    Annotation
)

class UpdateImmunizationRecord(BaseModel):
    '''Update Immunization Record '''
    resourceType: Literal["Immunization"] = Field(default='Immunization')
    status: Optional[code_types.status_codes]
    statusReason: Optional[CodeableConceptType]
    vaccineCode: Optional[CodeableConceptType]
    encounter: Optional[Reference]
    occurrenceDateTime: Optional[datetime.datetime] = FhirR4Fields.dateTime
    occurenceString: Optional[str] = FhirR4Fields.string
    recorded: Optional[datetime.date] = FhirR4Fields.date
    primarySource: Optional[bool] = FhirR4Fields.boolean
    reportOrigin: Optional[CodeableConceptType]
    location: Optional[Reference]
    manufacturer: Optional[Reference]
    lotNumber: Optional[str] = FhirR4Fields.string
    expirationDate: Optional[datetime.date] = FhirR4Fields.date
    site: Optional[CodeableConceptType]
    route: Optional[CodeableConceptType]
    doseQuantity: Optional[Quantity]
    performer: Optional[list[Performer]]
    note: Optional[list[Annotation]]
    reasonCode: Optional[list[CodeableConceptType]]
    reasonReference: Optional[list[Reference]]
    isSubpotent: Optional[bool] = FhirR4Fields.boolean
    subpotentReason: Optional[list[CodeableConceptType]]
    education: Optional[list[dict]]  # TODO: Education Model to be created
    procotolApplied: Optional[list[ProtocolApplied]]

    def dict(self, *args, **kwargs) -> dict[str, Any]:
        """
            Override the default dict method to exclude None values in the response
        """
        kwargs.pop('exclude_none', None)
        return super().dict(*args, exclude_none=True, **kwargs)

class UpdateSnomedModel(BaseModel):
    snomed_code: str = FhirR4Fields.string
    disease_type: str = FhirR4Fields.string
    description: str = FhirR4Fields.string
