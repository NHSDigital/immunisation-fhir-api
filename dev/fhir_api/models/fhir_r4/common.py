''' Common FHIR Data Models '''

from typing import (
    Optional,
    Any
)

from pydantic import (
    BaseModel,
    PositiveInt
    )

from datetime import datetime

import fhir_api.models.fhir_r4.code_types as code_types
from fhir_api.models.fhir_r4.fhir_datatype_fields import FhirR4Fields


class FhirBaseModel(BaseModel):
    ''' Base Model for FHIR Models '''
    def dict(self, *args, **kwargs) -> dict[str, Any]:
        """
            Override the default dict method to exclude None values in the response
        """
        kwargs.pop('exclude_none', None)
        return super().dict(*args, exclude_none=True, **kwargs)



class CodingType(FhirBaseModel):
    ''' Code Data Model '''
    system: Optional[str] = FhirR4Fields.string
    version: Optional[str] = FhirR4Fields.string
    code: Optional[str] = FhirR4Fields.string
    display: Optional[str] = FhirR4Fields.string
    userSelected: Optional[bool]


class CodeableConceptType(FhirBaseModel):
    ''' Codeable Concept Data Model '''
    coding: Optional[list[CodingType]]
    text: Optional[str] = FhirR4Fields.string


class Period(FhirBaseModel):
    '''  A time period defined by a start and end date/time. '''
    start: datetime = FhirR4Fields.dateTime
    end: Optional[datetime] = FhirR4Fields.dateTime


class HumanName(FhirBaseModel):
    '''
    A name of a human with text, parts and usage information.
    '''
    use: Optional[code_types.human_name_use]
    text: Optional[str] = FhirR4Fields.string
    family: Optional[str] = FhirR4Fields.string
    given: Optional[list[str]]
    prefix: Optional[list[str]]
    suffix: Optional[list[str]]
    period: Optional[Period]


class Quantity(FhirBaseModel):
    ''' Quantity Type '''
    value: Optional[float] = FhirR4Fields.decimal
    comparator: Optional[str] = FhirR4Fields.code
    unit: Optional[str] = FhirR4Fields.string
    system: Optional[str] = FhirR4Fields.uri
    code: Optional[str] = FhirR4Fields.code


class ContactPoint(FhirBaseModel):
    '''
    Details for all kinds of technology-mediated contact points
    for a person or organization, including telephone, email, etc.
    '''
    system: code_types.contact_point_system_types = None  # Required
    value: Optional[str] = FhirR4Fields.string
    use: Optional[code_types.contact_point_use_types]
    rank: Optional[PositiveInt] = FhirR4Fields.positiveInt
    period: Optional[Period]


class Address(FhirBaseModel):
    '''
    An address expressed using postal conventions (as opposed to GPS or other location definition formats).
    This data type may be used to convey addresses for use in delivering mail as well as for visiting
    locations which might not be valid for mail delivery.
    There are a variety of postal address formats defined around the world.
    '''
    use: Optional[code_types.address_use_type]
    type: Optional[code_types.address_type_type]
    text: Optional[str] = FhirR4Fields.string
    line: Optional[str] = FhirR4Fields.string
    city: Optional[str] = FhirR4Fields.string
    district: Optional[str] = FhirR4Fields.string
    state: Optional[str] = FhirR4Fields.string
    postalCode: Optional[str] = FhirR4Fields.string
    country: Optional[str] = FhirR4Fields.string
    period: Optional[Period]


class Reference(FhirBaseModel):
    ''' Reference data Model '''
    reference: Optional[str] = FhirR4Fields.string
    type: Optional[str] = FhirR4Fields.string
    identifier: Optional["Identifier"]
    display: Optional[str] = FhirR4Fields.string


class CodeableReference(FhirBaseModel):
    ''' Codeable Reference '''
    concept: Optional[CodeableConceptType]
    reference: Optional[Reference]


class Identifier(FhirBaseModel):
    ''' Identifier Data Model '''
    use_type: Optional[str] = FhirR4Fields.string
    type: Optional[CodeableConceptType]
    system: Optional[str] = FhirR4Fields.string
    value: Optional[str] = FhirR4Fields.string
    period: Optional[Period]
    assigner: Optional[Reference]


class Attachment(FhirBaseModel):
    ''' Attachment Model '''
    contentType: Optional[str] = FhirR4Fields.string
    language: Optional[str] = FhirR4Fields.string
    data: Optional[str] = FhirR4Fields.base64Binary
    url: Optional[str] = FhirR4Fields.url
    size: Optional[int] = FhirR4Fields.unsignedInt
    hash: Optional[str] = FhirR4Fields.base64Binary
    title: Optional[str] = FhirR4Fields.string
    creation: Optional[datetime] = FhirR4Fields.dateTime
