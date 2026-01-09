from dataclasses import fields, is_dataclass
from logging import config
import os
import re
import shutil
from typing import Type, Dict
import uuid
from pydantic import BaseModel
import pytest_check as check
from src.objectModels.api_data_objects import *
from src.objectModels.api_operation_outcome import OperationOutcome
from utilities.error_constants import ERROR_MAP
from utilities.date_helper import *

def empty_folder(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)


def find_entry_by_Imms_id(parsed_data, imms_id) -> Optional[object]:
    return next(
        (
            entry for entry in parsed_data.entry
            if entry.resource.resourceType == "Immunization" and entry.resource.id == imms_id
        ),
        None  
    )

def find_patient_by_fullurl(parsed_data) -> Optional[Entry]:
    for entry in parsed_data.entry:
        if entry.resource.resourceType == "Patient" :
            return entry
    return None


RESOURCE_MAP: Dict[str, Type[BaseModel]] = {
    "Immunization": FHIRImmunizationResponse,  
    "Patient": PatientResource, 
}

def parse_entry(entry_data: dict) -> Entry:
    resource_data = entry_data["resource"]
    resource_type = resource_data.get("resourceType", "").lower()  # ✅ Normalize case

    resource_class = RESOURCE_MAP.get(resource_type.capitalize())  # ✅ Match correct class

    if not resource_class:
        raise ValueError(f"Unsupported resourceType: {resource_type}")

    parsed_resource = resource_class.parse_obj(resource_data)
    parsed_search = Search.parse_obj(entry_data.get("search", {}))

    return Entry(
        fullUrl=entry_data.get("fullUrl"),
        resource=parsed_resource,
        search=parsed_search
    )

def is_valid_disease_type(disease_type: str) -> bool:
    valid_types = {"COVID", "FLU", "HPV", "MMR", "RSV", "SHINGLES", "MMRV", "PNEUMOCOCCAL", "MENACWY", "PERTUSSIS", "3IN1"}
    return disease_type in valid_types

def is_valid_nhs_number(nhs_number: str) -> bool:
    nhs_number = nhs_number.replace(" ", "")
    if not nhs_number.isdigit() or len(nhs_number) != 10:
        return False

    digits = [int(d) for d in nhs_number]
    total = sum((10 - i) * digits[i] for i in range(9))
    remainder = total % 11
    check_digit = 11 - remainder
    if check_digit == 11:
        check_digit = 0
    if check_digit == 10:
        return False
    return check_digit == digits[9]


def validate_error_response(error_response, errorName: str, imms_id: str = "", version: str = ""):
    uuid_obj = uuid.UUID(error_response.id, version=4)
    check.is_true(isinstance(uuid_obj, uuid.UUID), f"Id is not UUID {error_response.id}")

    fields_to_compare = []

    match errorName:
        case "not_found":
            expected_diagnostics = ERROR_MAP.get("not_found", {}).get("diagnostics", "").replace("<imms_id>", imms_id)
            fields_to_compare.append(("Diagnostics", expected_diagnostics, error_response.issue[0].diagnostics))

        case "invalid_etag":
            expected_diagnostics = ERROR_MAP.get("invalid_etag", {}).get("diagnostics", "").replace("<version>", version)
            fields_to_compare.append(("Diagnostics", expected_diagnostics, error_response.issue[0].diagnostics))
        case _:
            actual_diagnostics = (
                error_response.issue[0].diagnostics
                .replace('-  Date', '- Date')
                .replace('offsets.\nNote', 'offsets. Note')
                .replace('\n_', ' _')
                .replace('_\n ', '_')
                .replace('service.\n', 'service.')
                .replace('\n', '')
            )
            expected_diagnostics = ERROR_MAP.get(errorName, {}).get("diagnostics", "")
            fields_to_compare.append(("Diagnostics", expected_diagnostics, actual_diagnostics))

    fields_to_compare.extend([
        ("ResourceType", ERROR_MAP.get("Common_field", {}).get("resourceType", ""), error_response.resourceType),
        ("Meta_Profile", ERROR_MAP.get("Common_field", {}).get("profile", ""), error_response.meta.profile[0]),
        ("Issue_Code", ERROR_MAP.get(errorName, {}).get("code", "").lower(), error_response.issue[0].code.lower()),
        ("Coding_system", ERROR_MAP.get("Common_field", {}).get("system", ""), error_response.issue[0].details.coding[0].system),
        ("Coding_Code", ERROR_MAP.get(errorName, {}).get("code", "").lower(), error_response.issue[0].details.coding[0].code.lower()),
        ("severity", ERROR_MAP.get("Common_field", {}).get("severity", ""), error_response.issue[0].severity),
    ])

    for name, expected, actual in fields_to_compare:
        check.is_true(
            expected == actual,
            f"Expected {name}: {expected}, got {actual}"
        )


def parse_FHIR_immunization_response(json_data: dict) -> FHIRImmunizationResponse:
    return FHIRImmunizationResponse.parse_obj(json_data)  

def parse_read_response(json_data: dict) -> ImmunizationReadResponse_IntTable:
    return ImmunizationReadResponse_IntTable.parse_obj(json_data)  

def parse_error_response(json_data: dict) -> OperationOutcome:
    return OperationOutcome.parse_obj(json_data) 

def validate_to_compare_request_and_response(context, create_obj, created_event, table_validation: bool =False):
    request_patient = create_obj.contained[1]
    response_patient = created_event.patient

    expected_fullUrl = f"{context.baseUrl}/Immunization/{context.ImmsID}"
    
    referencePattern = r"^urn:uuid:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"   
    expected_occurrenceDateTime = covert_to_expected_date_format(create_obj.occurrenceDateTime)
    expected_recorded = covert_to_expected_date_format(create_obj.recorded)  
    actual_occurrenceDateTime = covert_to_expected_date_format(created_event.occurrenceDateTime)
    actual_recorded = covert_to_expected_date_format(created_event.recorded)

    fields_to_compare = []

    if not table_validation:
        fields_to_compare.append(("fullUrl", expected_fullUrl, context.created_event.fullUrl))
        fields_to_compare.append(("patient.identifier.system", request_patient.identifier[0].system, response_patient.identifier.system))
        fields_to_compare.append(("patient.identifier.value", request_patient.identifier[0].value, response_patient.identifier.value))
        fields_to_compare.append(("patient.reference", bool(re.match(referencePattern, response_patient.reference)), True))
        fields_to_compare.append(("meta.versionId", context.expected_version, int(created_event.meta.versionId))) 
    
    if table_validation:
        fields_to_compare.append(("Contained", create_obj.contained, created_event.contained))
        fields_to_compare.append(("patient.reference", create_obj.patient.reference, created_event.patient.reference))
        fields_to_compare.append(("performer", create_obj.performer, created_event.performer))
        fields_to_compare.append(("Id", context.ImmsID, created_event.id))
        
    fields_to_compare.extend([
        ("resourceType", create_obj.resourceType, created_event.resourceType),
        ("extension", create_obj.extension, created_event.extension),
        ("identifier.system", create_obj.identifier[0].system, created_event.identifier[0].system),
        ("identifier.value", create_obj.identifier[0].value, created_event.identifier[0].value),
        ("status", create_obj.status, created_event.status),
        ("vaccineCode", create_obj.vaccineCode, created_event.vaccineCode),       
        ("patient.type", create_obj.patient.type, created_event.patient.type),        
        ("occurrenceDateTime", expected_occurrenceDateTime, actual_occurrenceDateTime),
        ("Recorded", expected_recorded, actual_recorded),
        ("primarySource", create_obj.primarySource, created_event.primarySource),
        ("location", create_obj.location, created_event.location),
        ("manufacturer", create_obj.manufacturer, created_event.manufacturer),
        ("lotNumber", create_obj.lotNumber, created_event.lotNumber),
        ("expirationDate", create_obj.expirationDate, created_event.expirationDate),
        ("site", create_obj.site, created_event.site),
        ("route", create_obj.route, created_event.route),
        ("doseQuantity", create_obj.doseQuantity, created_event.doseQuantity),      
        # ("performer", create_obj.performer, created_event.performer),
        ("reasonCode", create_obj.reasonCode, created_event.reasonCode),
        ("protocolApplied", create_obj.protocolApplied, created_event.protocolApplied),
    ])

    for name, expected, actual in fields_to_compare:
        check.is_true(
                expected == actual,
                f"Expected {name}: {expected}, Actual {actual}"
            )
        
def extract_practitioner_name(response_practitioner):
    name_entry = next(iter(response_practitioner.name or []), None)

    family = getattr(name_entry, "family", "") or ""
    given = (getattr(name_entry, "given", []) or [""])[0]

    return {
        "Practitioner.name.family": family,
        "Practitioner.name.given": given
    }