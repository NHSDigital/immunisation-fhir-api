"""Constants for recordprocessor"""

import os

SOURCE_BUCKET_NAME = os.getenv("SOURCE_BUCKET_NAME")
ACK_BUCKET_NAME = os.getenv("ACK_BUCKET_NAME")
AUDIT_TABLE_NAME = os.getenv("AUDIT_TABLE_NAME")
AUDIT_TABLE_FILENAME_GSI = "filename_index"
AUDIT_TABLE_QUEUE_NAME_GSI = "queue_name_index"
FILE_NAME_PROC_LAMBDA_NAME = os.getenv("FILE_NAME_PROC_LAMBDA_NAME")

EXPECTED_CSV_HEADERS = [
    "NHS_NUMBER",
    "PERSON_FORENAME",
    "PERSON_SURNAME",
    "PERSON_DOB",
    "PERSON_GENDER_CODE",
    "PERSON_POSTCODE",
    "DATE_AND_TIME",
    "SITE_CODE",
    "SITE_CODE_TYPE_URI",
    "UNIQUE_ID",
    "UNIQUE_ID_URI",
    "ACTION_FLAG",
    "PERFORMING_PROFESSIONAL_FORENAME",
    "PERFORMING_PROFESSIONAL_SURNAME",
    "RECORDED_DATE",
    "PRIMARY_SOURCE",
    "VACCINATION_PROCEDURE_CODE",
    "VACCINATION_PROCEDURE_TERM",
    "DOSE_SEQUENCE",
    "VACCINE_PRODUCT_CODE",
    "VACCINE_PRODUCT_TERM",
    "VACCINE_MANUFACTURER",
    "BATCH_NUMBER",
    "EXPIRY_DATE",
    "SITE_OF_VACCINATION_CODE",
    "SITE_OF_VACCINATION_TERM",
    "ROUTE_OF_VACCINATION_CODE",
    "ROUTE_OF_VACCINATION_TERM",
    "DOSE_AMOUNT",
    "DOSE_UNIT_CODE",
    "DOSE_UNIT_TERM",
    "INDICATION_CODE",
    "LOCATION_CODE",
    "LOCATION_CODE_TYPE_URI",
]


class FileStatus:
    """File status constants"""

    QUEUED = "Queued"
    PROCESSING = "Processing"
    PROCESSED = "Processed"
    DUPLICATE = "Duplicate"


class AuditTableKeys:
    """Audit table keys"""

    FILENAME = "filename"
    MESSAGE_ID = "message_id"
    QUEUE_NAME = "queue_name"
    STATUS = "status"
    TIMESTAMP = "timestamp"


class Diagnostics:
    """Diagnostics messages"""

    INVALID_ACTION_FLAG = "Invalid ACTION_FLAG - ACTION_FLAG must be 'NEW', 'UPDATE' or 'DELETE'"
    NO_PERMISSIONS = "No permissions for requested operation"
    MISSING_UNIQUE_ID = "UNIQUE_ID or UNIQUE_ID_URI is missing"
    UNABLE_TO_OBTAIN_IMMS_ID = "Unable to obtain imms event id"
    UNABLE_TO_OBTAIN_VERSION = "Unable to obtain current imms event version"
    INVALID_CONVERSION = "Unable to convert row to FHIR Immunization Resource JSON format"


class Urls:
    """Urls"""

    SNOMED = "http://snomed.info/sct"
    NHS_NUMBER = "https://fhir.nhs.uk/Id/nhs-number"
    NULL_FLAVOUR_CODES = "http://terminology.hl7.org/CodeSystem/v3-NullFlavor"
    VACCINATION_PROCEDURE = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure"


class RedisCacheKeys:
    PERMISSIONS_CONFIG_FILE_KEY = "permissions_config.json"
    DISEASE_MAPPING_FILE_KEY = "disease_mapping.json"
