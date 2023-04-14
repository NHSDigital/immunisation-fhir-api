''' Patient Data Model based on Fhir Revision 4 spec '''

from datetime import datetime
from typing import Optional, Literal

import fhir_api.models.fhir_r4.code_types as code_types
from fhir_api.models.fhir_r4.fhir_datatype_fields import FhirR4Fields
from fhir_api.models.fhir_r4.common import (
    FhirBaseModel,
    Identifier,
    HumanName,
    ContactPoint,
    Address,
    CodeableConceptType,
    Attachment,
    Reference,
    Period,
)


class Contact(FhirBaseModel):
    ''' Contact Model '''
    relationship: Optional[list[CodeableConceptType]]
    name: Optional[HumanName]
    telecom: Optional[list[ContactPoint]]
    address: Optional[Address]
    gender: Optional[code_types.gender]
    organization: Optional[Reference]
    period: Optional[Period]


class Communication(FhirBaseModel):
    ''' Communication Model '''
    language: CodeableConceptType
    preferred: Optional[bool] = FhirR4Fields.boolean


class Link(FhirBaseModel):
    ''' Link Model '''
    other: Reference
    type: code_types.link_code


class Patient(FhirBaseModel):
    ''' Patient Base Model '''
    resourceType: Literal["Patient"]
    identifier: Optional[list[Identifier]]
    active: bool = FhirR4Fields.boolean
    name: list[HumanName]
    telecom: Optional[list[ContactPoint]]
    gender: Optional[code_types.gender]
    birthDate: Optional[str] = FhirR4Fields.date
    deceasedBoolean: Optional[bool] = FhirR4Fields.boolean
    deceasedDateTime: Optional[datetime] = FhirR4Fields.dateTime
    address: Optional[list[Address]]
    maritalStatus: Optional[CodeableConceptType]
    multipleBirthBoolean: Optional[bool] = FhirR4Fields.boolean
    multipleBirthInteger: Optional[int] = FhirR4Fields.integer
    photo: Optional[list[Attachment]]
    contact: Optional[list[Contact]]
    communication: Optional[list[Communication]]
    generalPractitioner: Optional[list[Reference]]
    managingOrganization: Optional[Reference]
    link: Optional[list[Link]]
