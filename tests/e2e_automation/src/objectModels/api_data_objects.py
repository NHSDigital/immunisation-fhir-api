from typing import  List, Literal, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from typing_extensions import Annotated


class ExtensionItem(BaseModel):
    url: str
    valueString: Optional[str] = None
    valueId: Optional[str] = None


class Coding(BaseModel):
    extension: Optional[List[ExtensionItem]] = None
    system: str
    code: Optional[str] = None
    display: Optional[str] = None

class CodeableConcept(BaseModel):
    coding: Optional[List[Coding]] = None
    text: Optional[str] = None 

class Period(BaseModel):
    start: str
    end: str

class Identifier(BaseModel):
    system: Optional[str] = None
    value: Optional[str] = None
    use: Optional[str] = None
    type: Optional[CodeableConcept] = None
    period: Optional[Period] = None

class Reference(BaseModel):
    reference: Optional[str] = None
    type: Optional[str] = None
    identifier: Optional[Identifier] = None

class HumanName(BaseModel):
    family: Optional[str] =None
    given: Optional[List[str]] = None

class Address(BaseModel):
    use: Optional[str] = None
    type: Optional[str] = None
    text: Optional[str] = None
    line: Optional[List[str]] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    postalCode: str
    country: Optional[str] = None
    period: Optional[Period]= None

class Practitioner(BaseModel):
    resourceType: str = "Practitioner"
    id: str
    name: List[HumanName]

class Patient(BaseModel):
    resourceType: str ="Patient"
    id: str
    identifier: Optional[List[Identifier]] = None
    name: List[HumanName]
    gender: str
    birthDate: str
    address: List[Address]

class Extension(BaseModel):
    url: str
    valueCodeableConcept: CodeableConcept

class Performer(BaseModel):
    actor: Reference  # Updated to match FHIR structure

class ReasonCode(BaseModel):
    coding: List[Coding]
    text: Optional[str] = None

class DoseQuantity(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    system: Optional[str] = None
    code: Optional[str] = None

class ProtocolApplied(BaseModel):
    targetDisease: List[CodeableConcept]
    doseNumberPositiveInt: Optional[int] = None
    doseNumberString: Optional[str] = None

class LocationIdentifier(BaseModel):
    system: str
    value: str

class Location(BaseModel):
    identifier: LocationIdentifier

class Immunization(BaseModel):
    resourceType: str = "Immunization"
    contained: List[Any]
    extension: List[Extension]
    identifier: List[Identifier]
    status: str = "completed"
    vaccineCode: CodeableConcept  # Fixed type
    patient: Reference  # Fixed type
    manufacturer: Dict[str, str]
    location: Location  
    site: CodeableConcept
    route: CodeableConcept
    doseQuantity: DoseQuantity
    performer: List[Performer]
    reasonCode: List[ReasonCode]
    protocolApplied: List[ProtocolApplied]
    occurrenceDateTime: str = ""
    recorded: str = ""
    primarySource: bool = True
    lotNumber: str = ""
    expirationDate: str = ""

    class Config:
        orm_mode = True 

class ResponseActorOrganization(BaseModel):
    type: str = "Organization"
    display: Optional[str] = None
    identifier: Optional[Identifier]  

class ResponsePerformer(BaseModel):
    actor: ResponseActorOrganization


class Link(BaseModel):
    relation: str
    url: str

class Search(BaseModel):
    mode: str

class PatientIdentifier(BaseModel):
    system: str
    value: Optional[str] = None

class ResponsePatient(BaseModel):
    reference: str
    type: Optional[str] = None
    identifier: Optional[PatientIdentifier] = None 
    
class Meta(BaseModel):
    versionId: str
class ImmunizationResponse(BaseModel):
    resourceType:  Literal["Immunization"]
    id: str
    meta: Meta
    extension: List[Extension]
    identifier: List[Identifier]
    status: str
    vaccineCode: CodeableConcept
    patient: ResponsePatient
    occurrenceDateTime: str
    recorded: str
    lotNumber: str
    expirationDate: str
    primarySource: bool
    location: Location
    manufacturer: Dict[str, Any]
    site: CodeableConcept
    route: CodeableConcept
    doseQuantity: DoseQuantity
    performer: Optional[List[ResponsePerformer]]
    reasonCode: List[ReasonCode]
    protocolApplied: List[ProtocolApplied]
    
class ImmunizationUpdate(BaseModel):
    resourceType:  Literal["Immunization"]
    id: str
    contained: List[Union[Patient, Practitioner]]
    extension: List[Extension]
    identifier: List[Identifier]
    status: str = "completed"
    vaccineCode: CodeableConcept  # Fixed type
    patient: Reference  # Fixed type
    manufacturer: Dict[str, str]
    location: Location  
    site: CodeableConcept
    route: CodeableConcept
    doseQuantity: DoseQuantity
    performer: List[Performer]
    reasonCode: List[ReasonCode]
    protocolApplied: List[ProtocolApplied]
    occurrenceDateTime: str = ""
    recorded: str = ""
    primarySource: bool = True
    lotNumber: str = ""
    expirationDate: str = ""

class PatientResource(BaseModel):
    resourceType: Literal["Patient"]
    id: str
    identifier: List[PatientIdentifier]

class Entry(BaseModel):
    fullUrl: str
    resource:Annotated[
        Union[ImmunizationResponse, PatientResource],
        Field(discriminator="resourceType")]
    search: Dict[str, str]

class FHIRImmunizationResponse(BaseModel):
    resourceType: str
    type: Optional[str] = None  
    link: Optional[List[Link]] = []  
    entry: Optional[List[Entry]] = []  
    total: Optional[int] = None

class ImmunizationReadResponse_IntTable(BaseModel):
    resourceType: str
    contained: List[Union[Patient, Practitioner]]
    extension: List[Extension]
    identifier: List[Identifier]
    status: str 
    vaccineCode: CodeableConcept
    patient: Reference
    manufacturer: Optional[Dict[str, str]] = None
    id: str
    location: Location  
    site: Optional[CodeableConcept] = None
    route: Optional[CodeableConcept] = None
    doseQuantity: Optional[DoseQuantity] = None
    performer: List[Performer]
    reasonCode: Optional[List[ReasonCode]] = None
    protocolApplied: List[ProtocolApplied]
    occurrenceDateTime: str = ""
    recorded: str = ""
    primarySource: bool = True
    lotNumber: str = ""
    expirationDate: str = ""