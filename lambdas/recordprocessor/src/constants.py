"""Constants for recordprocessor"""

import os
from enum import StrEnum

# Once Python projects are moved to /lambdas consider consolidating constants common to batch in
# /shared/src/common/constants/batch_constants.py (VED-881)
SOURCE_BUCKET_NAME = os.getenv("SOURCE_BUCKET_NAME")
ACK_BUCKET_NAME = os.getenv("ACK_BUCKET_NAME")
AUDIT_TABLE_NAME = os.getenv("AUDIT_TABLE_NAME")

ARCHIVE_DIR_NAME = "archive"
PROCESSING_DIR_NAME = "processing"

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
    PREPROCESSED = "Preprocessed"  # All entries in file converted to FHIR and forwarded to Kinesis
    PROCESSED = "Processed"  # All entries processed and ack file created
    NOT_PROCESSED = "Not processed"
    FAILED = "Failed"


class FileNotProcessedReason(StrEnum):
    """Reasons why a file was not processed"""

    UNAUTHORISED = "Unauthorised"
    EMPTY = "Empty file"


class AuditTableKeys:
    """Audit table keys"""

    FILENAME = "filename"
    MESSAGE_ID = "message_id"
    QUEUE_NAME = "queue_name"
    RECORD_COUNT = "record_count"
    STATUS = "status"
    TIMESTAMP = "timestamp"
    INGESTION_STARTED = "ingestion_started"
    ERROR_DETAILS = "error_details"


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

    SNOMED = "http://snomed.info/sct"  # NOSONAR(S5332)
    NHS_NUMBER = "https://fhir.nhs.uk/Id/nhs-number"
    NULL_FLAVOUR_CODES = "http://terminology.hl7.org/CodeSystem/v3-NullFlavor"  # NOSONAR(S5332)
    VACCINATION_PROCEDURE = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure"


class Operation(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class Permission(StrEnum):
    CREATE = "C"
    UPDATE = "U"
    DELETE = "D"


permission_to_operation_map = {
    Permission.CREATE: Operation.CREATE,
    Permission.UPDATE: Operation.UPDATE,
    Permission.DELETE: Operation.DELETE,
}
