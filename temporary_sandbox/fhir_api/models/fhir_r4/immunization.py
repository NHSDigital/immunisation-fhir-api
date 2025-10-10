"""Immunization Data Model based on Fhir Revision 4 spec"""

from typing import Optional, Literal, Any
from pydantic import BaseModel, PositiveInt
import datetime

import fhir_api.models.fhir_r4.code_types as code_types
from fhir_api.models.fhir_r4.fhir_datatype_fields import FhirR4Fields
from fhir_api.models.fhir_r4.common import (
    Identifier,
    CodeableConceptType,
    Reference,
    Quantity,
)


class Performer(BaseModel):
    function: Optional[CodeableConceptType]
    actor: Reference


class ProtocolApplied(BaseModel):
    series: Optional[str] = FhirR4Fields.string
    authority: Optional[Reference]
    targetDisease: Optional[list[CodeableConceptType]]
    doseNumberPositiveInt: Optional[PositiveInt] = FhirR4Fields.positiveInt
    doseNumberString: Optional[str] = FhirR4Fields.string
    seriesDosesPositiveInt: Optional[PositiveInt] = FhirR4Fields.positiveInt
    seriesDosesString: Optional[str] = FhirR4Fields.string


class Author(BaseModel):
    """Author Model"""

    authorRefernce: Optional[Reference]
    authorString: Optional[str] = FhirR4Fields.string


class Annotation(BaseModel):
    """Annotation Model"""

    author: Optional[Author]
    time: Optional[datetime.datetime] = FhirR4Fields.dateTime
    text: Optional[str] = FhirR4Fields.markdown


class Immunization(BaseModel):
    """Immunization Record for Reading"""

    resourceType: Literal["Immunization"]
    identifier: Optional[list[Identifier]]
    status: code_types.status_codes
    statusReason: Optional[CodeableConceptType]
    vaccineCode: CodeableConceptType
    patient: Reference
    encounter: Optional[Reference]
    occurrenceDateTime: Optional[datetime.datetime] = FhirR4Fields.dateTime
    occurenceString: Optional[str] = FhirR4Fields.string
    recorded: datetime.date = FhirR4Fields.date
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
        kwargs.pop("exclude_none", None)
        return super().dict(*args, exclude_none=True, **kwargs)
