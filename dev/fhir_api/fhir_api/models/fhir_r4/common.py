''' Common FHIR Data Models '''

from typing import (
    Optional,
)

from pydantic import (
    BaseModel,
    validator,
    PositiveInt
    )

from datetime import datetime

import fhir_api.models.fhir_r4.code_types as code_types
from fhir_api.models.fhir_r4.fhir_datatype_fields import FhirR4Fields


class CodingType(BaseModel):
    ''' Code Data Model '''
    system: Optional[str] = FhirR4Fields.string
    version: Optional[str] = FhirR4Fields.string
    code: Optional[str] = FhirR4Fields.string
    display: Optional[str] = FhirR4Fields.string
    userSelected: Optional[bool]


class CodeableConceptType(BaseModel):
    ''' Codeable Concept Data Model '''
    coding: Optional[list[CodingType]]
    text: Optional[str] = FhirR4Fields.string


class Period(BaseModel):
    '''  A time period defined by a start and end date/time. '''
    start: datetime = FhirR4Fields.dateTime
    end: datetime = FhirR4Fields.dateTime


class HumanName(BaseModel):
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


class Quantity(BaseModel):
    ''' Quantity Type '''
    value: Optional[float] = FhirR4Fields.decimal
    comparator: Optional[str] = FhirR4Fields.code
    unit: Optional[str] = FhirR4Fields.string
    system: Optional[str] = FhirR4Fields.uri
    code: Optional[str] = FhirR4Fields.code


class ContactPoint(BaseModel):
    '''
    Details for all kinds of technology-mediated contact points
    for a person or organization, including telephone, email, etc.
    '''
    system: code_types.contact_point_system_types = None  # Required
    value: Optional[str] = FhirR4Fields.string
    use: Optional[code_types.contact_point_use_types]
    rank: Optional[PositiveInt] = FhirR4Fields.positiveInt
    period: Optional[Period]

    @validator('system')
    def value_validator(cls, _v):
        ''' cpt-2: A system is required is a value is provided '''
        if cls.value:
            assert _v is None, "System must be populated if a value exists"
            return _v


class Address(BaseModel):
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


class Reference(BaseModel):
    ''' Reference data Model '''
    reference: Optional[str] = FhirR4Fields.string
    type: Optional[str] = FhirR4Fields.string
    identifier: Optional["Identifier"]
    display: Optional[str] = FhirR4Fields.string


class CodeableReference(BaseModel):
    ''' Codeable Reference '''
    concept: Optional[CodeableConceptType]
    reference: Optional[Reference]


class Identifier(BaseModel):
    ''' Identifier Data Model '''
    use_type: Optional[str] = FhirR4Fields.string
    type: Optional[CodeableConceptType]
    system: Optional[str] = FhirR4Fields.string
    value: Optional[str] = FhirR4Fields.string
    period: Optional[Period]
    assigner: Optional[Reference]


class Attachment(BaseModel):
    ''' Attachment Model '''
    contentType: Optional[str] = FhirR4Fields.string
    language: Optional[str] = FhirR4Fields.string
    data: Optional[str] = FhirR4Fields.base64Binary
    url: Optional[str] = FhirR4Fields.url
    size: Optional[int] = FhirR4Fields.unsignedInt
    hash: Optional[str] = FhirR4Fields.base64Binary
    title: Optional[str] = FhirR4Fields.string
    creation: Optional[datetime] = FhirR4Fields.dateTime
