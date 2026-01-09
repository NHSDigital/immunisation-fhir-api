from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import random
import uuid
from src.objectModels.api_data_objects import *
from utilities.vaccination_constants import *
from utilities.date_helper import *

def create_extension(url: str, stringValue: str = None, idValue: str = None) -> ExtensionItem:
    return ExtensionItem(
        url=url,
        valueString= stringValue ,
        valueId=idValue )
    
def build_vaccine_procedure_code(vaccine_type: str, text: str = None, add_extensions: bool = True) -> CodeableConcept:
    try:
        selected_vaccine_procedure = random.choice(VACCINATION_PROCEDURE_MAP[vaccine_type.upper()])
    except KeyError:
        raise ValueError(f"Unsupported vaccine type: {vaccine_type}")
    
    extensions = None
    if add_extensions:
        extensions = [
            create_extension("https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-CodingSCTDescDisplay", stringValue=selected_vaccine_procedure["stringValue"]),
            create_extension("http://hl7.org/fhir/StructureDefinition/coding-sctdescid", idValue=selected_vaccine_procedure["idValue"])
        ]

    return CodeableConcept(
        coding=[Coding(
            system=selected_vaccine_procedure["system"],
            code=selected_vaccine_procedure["code"],
            display=selected_vaccine_procedure["display"],
            extension=extensions
        )],
        text=text
    )

def build_vaccine_procedure_extension(vaccine_type: str, text: str = None) -> Extension: # type: ignore
    return Extension(
        url="https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
        valueCodeableConcept=build_vaccine_procedure_code(vaccine_type, text)  # type: ignore       
    )

def build_location_identifier() -> Location:
    return Location(
        identifier=LocationIdentifier(
            system="https://fhir.nhs.uk/Id/ods-organization-code",
            value="X99999"
        )
    )

def get_vaccine_details(vaccine_type: str, vacc_text: str = None, lot_number: str = "", expiry_date: str = "", add_extensions: bool = True) -> Dict[str, Any]:
    selected_vaccine = random.choice(VACCINE_CODE_MAP[vaccine_type.upper()])  

    extensions = None
    if add_extensions:
        extensions=[
            create_extension("https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-CodingSCTDescDisplay", stringValue=selected_vaccine["stringValue"]),
            create_extension("http://hl7.org/fhir/StructureDefinition/coding-sctdescid", idValue=selected_vaccine["idValue"])
        ]

    vaccine_code = CodeableConcept(
        coding=[Coding(
            system=selected_vaccine["system"],  
            code=selected_vaccine["code"], 
            display=selected_vaccine["display"],
            extension=extensions
        )],
        text=vacc_text
    )

    manufacturer = {"display": selected_vaccine["manufacturer"]}  

    if not lot_number:
        lot_number = str(random.randint(100000, 999999))

    if not expiry_date:
        future_date = datetime.now() + timedelta(days=365 * 2)  
        expiry_date = future_date.strftime('%Y-%m-%d')

    return {
        "vaccine_code": vaccine_code,
        "manufacturer": manufacturer,
        "lotNumber": lot_number,
        "expiryDate": expiry_date
    }


def build_performer() -> List[Performer]:
    return [
        Performer(actor=Reference(reference="#Pract1", type="Practitioner")),
        Performer(actor=Reference(
            reference="Organization/B0C4P",  
            type="Organization",
            identifier=Identifier(
                value="B0C4P",
                system="https://fhir.nhs.uk/Id/ods-organization-code",
                use="usual",
                type=CodeableConcept(
                    coding=[
                        Coding(
                            system="http://terminology.hl7.org/CodeSystem/v2-0203",
                            code="123456",
                            display="Test display performer",
                            version="Test version performer",
                            userSelected=True
                        )
                    ],
                    text="test string performer"
                ),
                period=Period(
                    start="2000-01-01",
                    end="2025-01-01"
                )
            ),
            display="UNIVERSITY HOSPITAL OF WALES"
        ))
    ]

def remove_empty_fields(data):
    """ Recursively removes fields with empty values from a dictionary. """
    if isinstance(data, dict):
        return {k: remove_empty_fields(v) for k, v in data.items() if v != ""}
    elif isinstance(data, list):
        return [remove_empty_fields(item) for item in data]
    else:
        return data

def build_site_route(obj: Coding, text: str = None, add_extensions: bool = True) -> CodeableConcept:
    
    extensions = None
    if add_extensions:
        extensions=[
            create_extension("https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-CodingSCTDescDisplay", stringValue=obj["stringValue"]),
            create_extension("http://hl7.org/fhir/StructureDefinition/coding-sctdescid", idValue=obj["idValue"])
        ]

    return CodeableConcept(
        coding=[Coding(
        system=obj["system"],
        code=obj["code"],
        display=obj["display"],
        extension=extensions
    )],
        text=text
    )
    
def build_protocol_applied(vaccine_type: str, doseNumber: int = 1) -> ProtocolApplied:
    list_of_diseases = PROTOCOL_DISEASE_MAP.get(vaccine_type.upper(), [])
    return ProtocolApplied(
        targetDisease=[
            CodeableConcept(
                coding=[
                    Coding(
                        system=disease["system"],
                        code=disease["code"],
                        display=disease["display"],
                        extension=None
                    )
                ]
            )
            for disease in list_of_diseases
        ],
        doseNumberPositiveInt=doseNumber
    )

def create_immunization_object(patient, vaccine_type: str) -> Immunization:
    practitioner = Practitioner(
        resourceType="Practitioner",  # ✅ Explicitly set resourceType
        id="Pract1",  
        name=[HumanName(family="Furlong", given=["Darren"])]
    )
    extension = [build_vaccine_procedure_extension(vaccine_type.upper())]
    vaccine_details = get_vaccine_details(vaccine_type)  

    return Immunization(
        resourceType="Immunization",
        contained=[practitioner, patient],
        extension=extension,
        identifier=[Identifier(system="https://supplierABC/identifiers/vacc", value=str(uuid.uuid4()))],
        vaccineCode=vaccine_details["vaccine_code"], 
        patient=Reference(reference=f"#{patient.id}", type="Patient"),  
        occurrenceDateTime=generate_date("current_occurrence"),
        recorded=generate_date("current_occurrence"),
        manufacturer=vaccine_details["manufacturer"],
        location=build_location_identifier(),
        lotNumber=vaccine_details["lotNumber"],
        status="completed",
        primarySource= True,
        expirationDate=vaccine_details["expiryDate"],
        site=build_site_route(random.choice(SITE_MAP)),
        route=build_site_route(random.choice(ROUTE_MAP)),
        doseQuantity=DoseQuantity(**random.choice(DOSE_QUANTITY_MAP)),
        performer=build_performer(),
        reasonCode=[CodeableConcept(coding=[random.choice(REASON_CODE_MAP)])],
        protocolApplied=[build_protocol_applied(vaccine_type.upper())]
    )
    

def convert_to_update(immunization: Immunization, id: str) -> ImmunizationUpdate:
    return ImmunizationUpdate(
        resourceType=immunization.resourceType,
        id=id,
        contained=immunization.contained, 
        extension=immunization.extension,
        identifier=immunization.identifier,
        status=immunization.status,
        vaccineCode=immunization.vaccineCode,
        patient=immunization.patient,  
        occurrenceDateTime=immunization.occurrenceDateTime,
        recorded=immunization.recorded,
        lotNumber=immunization.lotNumber,
        expirationDate=immunization.expirationDate,
        primarySource=immunization.primarySource,
        location=immunization.location,
        manufacturer=immunization.manufacturer,
        site=immunization.site,
        route=immunization.route,
        doseQuantity=immunization.doseQuantity,
        performer=immunization.performer, 
        reasonCode=immunization.reasonCode,
        protocolApplied=immunization.protocolApplied
    )

