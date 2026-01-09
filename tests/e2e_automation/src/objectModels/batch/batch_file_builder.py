from typing import Dict, Any, Optional
import uuid
import random
import re
from src.objectModels.batch.batch_data_object import BatchVaccinationRecord
from utilities.enums import GenderCode
from utilities.vaccination_constants import (
    VACCINATION_PROCEDURE_MAP, VACCINE_CODE_MAP, SITE_MAP, ROUTE_MAP
)
from utilities.date_helper import generate_date
from src.objectModels.patient_loader import load_patient_by_id
import csv


def build_procedure_code(vaccine_type: str) -> Dict[str, str]:
    try:
        selected = random.choice(VACCINATION_PROCEDURE_MAP[vaccine_type.upper()])
        return {"term": selected["display"], "code": selected["code"]}
    except KeyError:
        raise ValueError(f"Unsupported vaccine type: {vaccine_type}")

def build_vaccine_details(vaccine_type: str, lot_number: str = "", expiry_date: str = "") -> Dict[str, Any]:
    try:
        selected = random.choice(VACCINE_CODE_MAP[vaccine_type.upper()])
    except KeyError:
        raise ValueError(f"Unsupported vaccine type: {vaccine_type}")

    return {
        "term": selected["display"],
        "code": selected["code"],
        "manufacturer": selected["manufacturer"],
        "lot_number": lot_number or str(random.randint(100000, 999999)),
        "expiry_date": expiry_date or generate_date("current_date").replace("-", "")
    }

def build_location_site_identifier(value: str = 'X99999') -> Dict[str, str]:
    return {
        "system": "https://fhir.nhs.uk/Id/ods-organization-code",
        "value": value
    }

def get_batch_date(date_str: str = "current_occurrence") -> str:
    raw_date = generate_date(date_str)
    cleaned_date = re.sub(r"[^\w]", "", raw_date)
    return cleaned_date


def get_performing_professional(forename: str = 'Automation', surname: str = 'Tests') -> Dict[str, str]:
    return {
        "performing_professional_forename": forename,
        "performing_professional_surname": surname
    }

def build_site_of_vaccination() -> Dict[str, str]:
    selected = random.choice(SITE_MAP)
    return {
        "site_of_vaccination_code": selected["code"],
        "site_of_vaccination_term": selected["display"]
    }

def build_route_of_vaccination() -> Dict[str, str]:
    selected = random.choice(ROUTE_MAP)
    return {
        "route_of_vaccination_code": selected["code"],
        "route_of_vaccination_term": selected["display"]
    }

def build_dose_details(
    dose_sequence: str = "1",
    dose_amount: str = "0.5",
    dose_unit_code: str = "ml",
    dose_unit_term: str = "millilitre"
) -> Dict[str, str]:
    return {
        "dose_sequence": dose_sequence,
        "dose_amount": dose_amount,
        "dose_unit_code": dose_unit_code,
        "dose_unit_term": dose_unit_term
    }

def build_unique_reference(unique_id: Optional[str] = None) -> Dict[str, str]:
    uid = unique_id or str(uuid.uuid4())
    return {
        "unique_id": uid,
        "unique_id_uri": "https://fhir.nhs.uk/Id/Automation-vaccine-administered-event-uk"
    }

def get_patient_details(context) -> Dict[str, str]:
    patient = load_patient_by_id(context.patient_id)
    return {
        "first_name": patient.name[0].given[0],
        "last_name": patient.name[0].family,
        "nhs_number": patient.identifier[0].value,
        "gender": GenderCode[patient.gender].value,
        "birth_date": patient.birthDate.replace("-", ""),
        "postal_code": patient.address[0].postalCode
    }

def generate_file_name(context) -> str:
    return f"{context.vaccine_type}_Vaccinations_v5_{context.supplier_ods_code}_{context.FileTimestamp}.{context.file_extension}"

def build_batch_file(context, unique_id: str = None) -> BatchVaccinationRecord:
    patient = get_patient_details(context)
    location = build_location_site_identifier()
    procedure = build_procedure_code(context.vaccine_type)
    vaccine = build_vaccine_details(context.vaccine_type)
    professional = get_performing_professional()
    site = build_site_of_vaccination()
    route = build_route_of_vaccination()
    dose = build_dose_details()
    unique = build_unique_reference(unique_id)

    return BatchVaccinationRecord(
        NHS_NUMBER=patient["nhs_number"],
        PERSON_FORENAME=patient["first_name"],
        PERSON_SURNAME=patient["last_name"],
        PERSON_DOB=patient["birth_date"],
        PERSON_GENDER_CODE=patient["gender"],
        PERSON_POSTCODE=patient["postal_code"],
        DATE_AND_TIME=get_batch_date("current_occurrence_with_milliseconds"),
        SITE_CODE=location["value"],
        SITE_CODE_TYPE_URI=location["system"],
        UNIQUE_ID=unique["unique_id"],
        UNIQUE_ID_URI=unique["unique_id_uri"],
        ACTION_FLAG="NEW",
        PERFORMING_PROFESSIONAL_FORENAME=professional["performing_professional_forename"],
        PERFORMING_PROFESSIONAL_SURNAME=professional["performing_professional_surname"],
        RECORDED_DATE=get_batch_date("current_date"),
        PRIMARY_SOURCE="TRUE",
        VACCINATION_PROCEDURE_CODE=procedure["code"],
        VACCINATION_PROCEDURE_TERM=procedure["term"],
        DOSE_SEQUENCE=dose["dose_sequence"],
        VACCINE_PRODUCT_CODE=vaccine["code"],
        VACCINE_PRODUCT_TERM=vaccine["term"],
        VACCINE_MANUFACTURER=vaccine["manufacturer"],
        BATCH_NUMBER=vaccine["lot_number"],
        EXPIRY_DATE=vaccine["expiry_date"],
        SITE_OF_VACCINATION_CODE=site["site_of_vaccination_code"],
        SITE_OF_VACCINATION_TERM=site["site_of_vaccination_term"],
        ROUTE_OF_VACCINATION_CODE=route["route_of_vaccination_code"],
        ROUTE_OF_VACCINATION_TERM=route["route_of_vaccination_term"],
        DOSE_AMOUNT=dose["dose_amount"],
        DOSE_UNIT_CODE=dose["dose_unit_code"],
        DOSE_UNIT_TERM=dose["dose_unit_term"],
        INDICATION_CODE="443684005",
        LOCATION_CODE=location["value"],
        LOCATION_CODE_TYPE_URI=location["system"]
    )
    
def save_record_to_batch_files_directory(context, delimiter):
    file_path = f"{context.working_directory}/{context.filename}"
    df = context.vaccine_df.copy()
    df.reset_index(drop=True, inplace=True)

    with open(file_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter=delimiter, quoting=csv.QUOTE_ALL)
        writer.writerow(df.columns.tolist())  
        for row in df.itertuples(index=False):
            writer.writerow(row)

    print(f"✅ Pipe-delimited file saved to: {file_path}")


