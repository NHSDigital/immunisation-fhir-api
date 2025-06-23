"""Function to process a single row of a csv file"""

from convert_to_fhir_imms_resource import convert_to_fhir_imms_resource
from constants import Diagnostics
from mappings import Vaccine
from clients import logger
from utils_for_recordprocessor import create_diagnostics_dictionary


def process_row(vaccine: Vaccine, allowed_operations: set, row: dict) -> dict:
    """
    Processes a row of the file and returns a dictionary containing the fhir_json, action_flag, imms_id, local_id
    (where applicable), version(where applicable) and any diagnostics.
    The local_id is combination of unique_id and unique_id_uri combined by "^"
    """
    action_flag = (row.get("ACTION_FLAG") or "").upper()
    unique_id_uri = row.get("UNIQUE_ID_URI")
    unique_id = row.get("UNIQUE_ID")
    local_id = f"{unique_id}^{unique_id_uri}"

    # Handle invalid action_flag
    if action_flag not in ("NEW", "UPDATE", "DELETE"):
        logger.info("Invalid ACTION_FLAG '%s' - ACTION_FLAG MUST BE 'NEW', 'UPDATE' or 'DELETE'", action_flag)
        return {
            "diagnostics": create_diagnostics_dictionary("INVALID_ACTION_FLAG", 400, Diagnostics.INVALID_ACTION_FLAG),
            "operation_requested": action_flag,
            "local_id": local_id,
        }

    operation_requested = action_flag.replace("NEW", "CREATE")
    logger.info("OPERATION REQUESTED:  %s", operation_requested)
    logger.info("OPERATION ALLOWED: %s", allowed_operations)

    # Handle no permissions
    if operation_requested not in allowed_operations:
        logger.info("Skipping row as supplier does not have the permissions for this operation %s", operation_requested)
        return {
            "diagnostics": create_diagnostics_dictionary("NO_PERMISSIONS", 403, Diagnostics.NO_PERMISSIONS),
            "operation_requested": operation_requested,
            "local_id": local_id,
        }

    # Handle missing UNIQUE_ID or UNIQUE_ID_URI
    if not (row.get("UNIQUE_ID_URI") and row.get("UNIQUE_ID")):
        logger.error("Invalid row format: row is missing either UNIQUE_ID or UNIQUE_ID_URI")
        return {
            "diagnostics": create_diagnostics_dictionary("MISSING_UNIQUE_ID", 400, Diagnostics.MISSING_UNIQUE_ID),
            "operation_requested": operation_requested,
            "local_id": local_id,
        }

    # Handle success
    return {
        "fhir_json": convert_to_fhir_imms_resource(row, vaccine),
        "operation_requested": operation_requested,
        "local_id": local_id,
    }
