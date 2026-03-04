from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from src.objectModels.api_operation_outcome import OperationOutcome


class ExtensionItem(BaseModel):
    url: str
    valueString: str | None = None
    valueId: str | None = None


class Coding(BaseModel):
    extension: list[ExtensionItem] | None = None
    system: str
    code: str | None = None
    display: str | None = None


class CodeableConcept(BaseModel):
    coding: list[Coding] | None = None
    text: str | None = None


class Period(BaseModel):
    start: str
    end: str


class Identifier(BaseModel):
    system: str | None = None
    value: str | None = None
    use: str | None = None
    type: CodeableConcept | None = None
    period: Period | None = None


class Reference(BaseModel):
    reference: str | None = None
    type: str | None = None
    identifier: Identifier | None = None


class HumanName(BaseModel):
    family: str | None = None
    given: list[str] | None = None


class Address(BaseModel):
    use: str | None = None
    type: str | None = None
    text: str | None = None
    line: list[str] | None = None
    city: str | None = None
    district: str | None = None
    state: str | None = None
    postalCode: str
    country: str | None = None
    period: Period | None = None


class Practitioner(BaseModel):
    resourceType: str = "Practitioner"
    id: str
    name: list[HumanName]


class Patient(BaseModel):
    resourceType: str = "Patient"
    id: str
    identifier: list[Identifier] | None = None
    name: list[HumanName]
    gender: str
    birthDate: str
    address: list[Address]


class Extension(BaseModel):
    url: str
    valueCodeableConcept: CodeableConcept


class Performer(BaseModel):
    actor: Reference  # Updated to match FHIR structure


class ReasonCode(BaseModel):
    coding: list[Coding]
    text: str | None = None


class DoseQuantity(BaseModel):
    value: float | None = None
    unit: str | None = None
    system: str | None = None
    code: str | None = None


class ProtocolApplied(BaseModel):
    targetDisease: list[CodeableConcept]
    doseNumberPositiveInt: int | None = None
    doseNumberString: str | None = None


class LocationIdentifier(BaseModel):
    system: str
    value: str


class Location(BaseModel):
    identifier: LocationIdentifier


class Immunization(BaseModel):
    resourceType: str = "Immunization"
    contained: list[Any]
    extension: list[Extension]
    identifier: list[Identifier]
    status: str = "completed"
    vaccineCode: CodeableConcept  # Fixed type
    patient: Reference  # Fixed type
    manufacturer: dict[str, str]
    location: Location
    site: CodeableConcept
    route: CodeableConcept
    doseQuantity: DoseQuantity
    performer: list[Performer]
    reasonCode: list[ReasonCode]
    protocolApplied: list[ProtocolApplied]
    occurrenceDateTime: str = ""
    recorded: str = ""
    primarySource: bool = True
    lotNumber: str = ""
    expirationDate: str = ""

    class Config:
        orm_mode = True


class ResponseActorOrganization(BaseModel):
    type: str = "Organization"
    display: str | None = None
    identifier: Identifier | None


class ResponsePerformer(BaseModel):
    actor: ResponseActorOrganization


class Link(BaseModel):
    relation: str
    url: str


class Search(BaseModel):
    mode: str


class PatientIdentifier(BaseModel):
    system: str
    value: str | None = None


class ResponsePatient(BaseModel):
    reference: str
    type: str | None = None
    identifier: PatientIdentifier | None = None


class Meta(BaseModel):
    versionId: str


class ImmunizationResponse(BaseModel):
    resourceType: Literal["Immunization"]
    id: str
    meta: Meta
    extension: list[Extension]
    identifier: list[Identifier]
    status: str
    vaccineCode: CodeableConcept
    patient: ResponsePatient
    occurrenceDateTime: str
    recorded: str
    lotNumber: str
    expirationDate: str
    primarySource: bool
    location: Location
    manufacturer: dict[str, Any]
    site: CodeableConcept
    route: CodeableConcept
    doseQuantity: DoseQuantity
    performer: list[ResponsePerformer] | None
    reasonCode: list[ReasonCode]
    protocolApplied: list[ProtocolApplied]


class ImmunizationUpdate(BaseModel):
    resourceType: Literal["Immunization"]
    id: str
    contained: list[Patient | Practitioner]
    extension: list[Extension]
    identifier: list[Identifier]
    status: str = "completed"
    vaccineCode: CodeableConcept  # Fixed type
    patient: Reference  # Fixed type
    manufacturer: dict[str, str]
    location: Location
    site: CodeableConcept
    route: CodeableConcept
    doseQuantity: DoseQuantity
    performer: list[Performer]
    reasonCode: list[ReasonCode]
    protocolApplied: list[ProtocolApplied]
    occurrenceDateTime: str = ""
    recorded: str = ""
    primarySource: bool = True
    lotNumber: str = ""
    expirationDate: str = ""


class PatientResource(BaseModel):
    resourceType: Literal["Patient"]
    id: str
    identifier: list[PatientIdentifier]


class Entry(BaseModel):
    fullUrl: str | None = None
    resource: Annotated[ImmunizationResponse | PatientResource | OperationOutcome, Field(discriminator="resourceType")]
    search: dict[str, str] | None = None


class FHIRImmunizationResponse(BaseModel):
    resourceType: str
    type: str | None = None
    link: list[Link] | None = []
    entry: list[Entry] | None = []
    total: int | None = None


class ImmunizationReadResponse_IntTable(BaseModel):
    resourceType: str
    contained: list[Patient | Practitioner]
    extension: list[Extension]
    identifier: list[Identifier]
    status: str
    vaccineCode: CodeableConcept
    patient: Reference
    manufacturer: dict[str, str] | None = None
    id: str
    location: Location
    site: CodeableConcept | None = None
    route: CodeableConcept | None = None
    doseQuantity: DoseQuantity | None = None
    performer: list[Performer]
    reasonCode: list[ReasonCode] | None = None
    protocolApplied: list[ProtocolApplied]
    occurrenceDateTime: str = ""
    recorded: str = ""
    primarySource: bool = True
    lotNumber: str = ""
    expirationDate: str = ""
