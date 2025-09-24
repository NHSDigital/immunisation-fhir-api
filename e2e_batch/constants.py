import os
from datetime import datetime, timezone

environment = os.environ.get("ENVIRONMENT", "internal-dev")
REGION = "eu-west-2"

SOURCE_BUCKET = f"immunisation-batch-{environment}-data-sources"
INPUT_PREFIX = ""
ACK_BUCKET = f"immunisation-batch-{environment}-data-destinations"
FORWARDEDFILE_PREFIX = "forwardedFile/"
PRE_VALIDATION_ERROR = "Validation errors: doseQuantity.value must be a number"
POST_VALIDATION_ERROR = "Validation errors: contained[?(@.resourceType=='Patient')].name[0].given is a mandatory field"
DUPLICATE = "The provided identifier:"
ACK_PREFIX = "ack/"
TEMP_ACK_PREFIX = "TempAck/"
HEADER_RESPONSE_CODE_COLUMN = "HEADER_RESPONSE_CODE"
FILE_NAME_VAL_ERROR = "Infrastructure Level Response Value - Processing Error"
CONFIG_BUCKET = "imms-internal-dev-supplier-config"
PERMISSIONS_CONFIG_FILE_KEY = "permissions_config.json"
RAVS_URI = "https://www.ravs.england.nhs.uk/"
batch_fifo_queue_name = f"imms-{environment}-batch-file-created-queue.fifo"
ack_metadata_queue_name = f"imms-{environment}-ack-metadata-queue.fifo"
audit_table_name = f"immunisation-batch-{environment}-audit-table"


class EventName():
    CREATE = "INSERT"
    UPDATE = "MODIFY"
    DELETE_LOGICAL = "MODIFY"
    DELETE_PHYSICAL = "REMOVE"


class Operation():
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE_LOGICAL = "DELETE"
    DELETE_PHYSICAL = "REMOVE"


class ActionFlag():
    CREATE = "NEW"
    UPDATE = "UPDATE"
    DELETE_LOGICAL = "DELETE"
    NONE = "NONE"


class InfResult:
    SUCCESS = "Success"
    PARTIAL_SUCCESS = "Partial Success"
    FATAL_ERROR = "Fatal Error"


class BusRowResult():
    SUCCESS = "OK"
    FATAL_ERROR = "Fatal Error"
    IMMS_NOT_FOUND = "Immunization resource does not exist"
    NONE = "NONE"


class OperationOutcome:
    IMMS_NOT_FOUND = "Immunization resource does not exist"
    TEST = "TEST"


class OpMsgs:
    VALIDATION_ERROR = "Validation errors"
    MISSING_MANDATORY_FIELD = "is a mandatory field"
    DOSE_QUANTITY_NOT_NUMBER = "doseQuantity.value must be a number"
    IMM_NOT_EXIST = "Immunization resource does not exist"
    IDENTIFIER_PROVIDED = "The provided identifier:"
    INVALID_DATE_FORMAT = "is not in the correct format"


class DestinationType:
    INF = ACK_PREFIX
    BUS = FORWARDEDFILE_PREFIX


class ActionSequence():
    def __init__(self, desc: str, actions: list[ActionFlag], outcome: ActionFlag = None):
        self.actions = actions
        self.description = desc
        self.outcome = outcome if outcome else actions[-1]


class PermPair():
    def __init__(self, ods_code: str, permissions: str):
        self.ods_code = ods_code
        self.permissions = permissions


class TestSet():
    CREATE_OK = ActionSequence("Create. OK", [ActionFlag.CREATE])
    UPDATE_OK = ActionSequence("Update. OK", [ActionFlag.CREATE, ActionFlag.UPDATE])
    DELETE_OK = ActionSequence("Delete. OK", [ActionFlag.CREATE, ActionFlag.UPDATE, ActionFlag.DELETE_LOGICAL])
    REINSTATE_OK = ActionSequence("Reinstate. OK", [ActionFlag.CREATE, ActionFlag.DELETE_LOGICAL, ActionFlag.UPDATE])
    DELETE_FAIL = ActionSequence("Delete without Create. Fail", [ActionFlag.DELETE_LOGICAL])
    UPDATE_FAIL = ActionSequence("Update without Create. Fail", [ActionFlag.UPDATE], outcome=ActionFlag.NONE)


def create_row(unique_id, dose_amount, action_flag: str, header, inject_char=None):
    """Helper function to create a single row with the specified UNIQUE_ID and ACTION_FLAG."""

    name = "James" if not inject_char else b'Jam\xe9s'
    return {
        header: "9732928395",
        "PERSON_FORENAME": "PHYLIS",
        "PERSON_SURNAME": name,
        "PERSON_DOB": "20080217",
        "PERSON_GENDER_CODE": "0",
        "PERSON_POSTCODE": "WD25 0DZ",
        "DATE_AND_TIME": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"),
        "SITE_CODE": "RVVKC",
        "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
        "UNIQUE_ID": unique_id,
        "UNIQUE_ID_URI": RAVS_URI,
        "ACTION_FLAG": action_flag,
        "PERFORMING_PROFESSIONAL_FORENAME": "PHYLIS",
        "PERFORMING_PROFESSIONAL_SURNAME": name,
        "RECORDED_DATE": datetime.now(timezone.utc).strftime("%Y%m%d"),
        "PRIMARY_SOURCE": "TRUE",
        "VACCINATION_PROCEDURE_CODE": "956951000000104",
        "VACCINATION_PROCEDURE_TERM": "RSV vaccination in pregnancy (procedure)",
        "DOSE_SEQUENCE": "1",
        "VACCINE_PRODUCT_CODE": "42223111000001107",
        "VACCINE_PRODUCT_TERM": "Quadrivalent influenza vaccine (Sanofi Pasteur)",
        "VACCINE_MANUFACTURER": "Sanofi Pasteur",
        "BATCH_NUMBER": "BN92478105653",
        "EXPIRY_DATE": "20240915",
        "SITE_OF_VACCINATION_CODE": "368209003",
        "SITE_OF_VACCINATION_TERM": "Right arm",
        "ROUTE_OF_VACCINATION_CODE": "1210999013",
        "ROUTE_OF_VACCINATION_TERM": "Intradermal use",
        "DOSE_AMOUNT": dose_amount,
        "DOSE_UNIT_CODE": "2622896019",
        "DOSE_UNIT_TERM": "Inhalation - unit of product usage",
        "INDICATION_CODE": "1037351000000105",
        "LOCATION_CODE": "RJC02",
        "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
    }
