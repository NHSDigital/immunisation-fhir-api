"""Function to send the request directly to lambda (or return appropriate diagnostics if this is not possible)"""

import logging
from models.errors import MessageNotSuccessfulError, IdNotFoundError
# from get_imms_id_and_version import get_imms_id_and_version
# from clients import lambda_client
# from utils_for_record_forwarder import invoke_lambda
from constants import Constants
from fhir_controller import FhirController
# from log_structure import forwarder_function_info

logger = logging.getLogger()


def send_create_request(controller: FhirController, fhir_json: dict, supplier: str) -> str:
    """Sends the create request and handles the response. Returns the imms_id."""
    # Send create request
    headers = {"SupplierSystem": Constants.IMMS_BATCH_APP_NAME, "BatchSupplierSystem": supplier}
    payload = {"headers": headers, "body": fhir_json}
    response = controller.create_immunization(payload)
    return response


def send_update_request(controller: FhirController, fhir_json: dict, supplier: str) -> str:
    """Obtains the imms_id, sends the update request and handles the response. Returns the imms_id."""
    # Obtain imms_id and version
    try:
        imms_id, version = get_imms_id_and_version(controller, fhir_json)
    except IdNotFoundError as error:
        raise MessageNotSuccessfulError(error) from error
    if not imms_id:
        raise MessageNotSuccessfulError("Unable to obtain Imms ID")
    if not version:
        raise MessageNotSuccessfulError("Unable to obtain Imms version")

    # Send update request
    fhir_json["id"] = imms_id
    headers = {"SupplierSystem": Constants.IMMS_BATCH_APP_NAME, "BatchSupplierSystem": supplier, "E-Tag": version}
    payload = {"headers": headers, "body": fhir_json, "pathParameters": {"id": imms_id}}
    response = controller.update_immunization(payload)
    return response


def send_delete_request(controller: FhirController, fhir_json: dict, supplier: str) -> str:
    """Sends the delete request and handles the response. Returns the imms_id."""
    # Obtain imms_id
    try:
        imms_id, _ = get_imms_id_and_version(controller, fhir_json)
    except IdNotFoundError as error:
        raise MessageNotSuccessfulError(error) from error
    if not imms_id:
        raise MessageNotSuccessfulError("Unable to obtain Imms ID")

    # Send delete request
    headers = {"SupplierSystem": Constants.IMMS_BATCH_APP_NAME, "BatchSupplierSystem": supplier}
    payload = {"headers": headers, "body": fhir_json, "pathParameters": {"id": imms_id}}
    response = controller.delete_immunization(payload)
    return response


def get_imms_id_and_version(controller: FhirController, fhir_json: dict) -> tuple[str, int]:
    """Send a GET request to Imms API requesting the id and version"""
    # Create payload
    headers = {"SupplierSystem": Constants.IMMS_BATCH_APP_NAME}
    identifier = fhir_json.get("identifier", [{}])[0]
    immunization_identifier = f"{identifier.get('system')}|{identifier.get('value')}"
    query_string_parameters = {"_element": "id,meta", "immunization.identifier": immunization_identifier}
    payload = {"headers": headers, "body": None, "queryStringParameters": query_string_parameters}

    # Invoke lambda
    status_code, body, _ = controller.get_immunization_by_identifier(payload)

    # Handle non-200 or empty response
    if not (body.get("total") == 1 and status_code == 200):
        logger.error("imms_id not found:%s and status_code: %s", body, status_code)
        raise IdNotFoundError("Imms id not found")

    # Return imms_id and version
    resource = body.get("entry", [])[0]["resource"]
    return resource.get("id"), resource.get("meta", {}).get("versionId")


def get_operation_outcome_diagnostics(body: dict) -> str:
    """
    Returns the diagnostics from the API response. If the diagnostics can't be found in the API response,
    returns a default diagnostics string
    """
    try:
        return body.get("issue")[0].get("diagnostics")
    except (AttributeError, IndexError):
        return "Unable to obtain diagnostics from API response"


def send_request_to_controller(controller: FhirController, message_body: dict) -> str:
    """
    Sends request to the Imms API (unless there was a failure at the recordprocessor level). Returns the imms id.
    If message is not successfully received and accepted by the Imms API raises a MessageNotSuccessful Error.
    """
    if incoming_diagnostics := message_body.get("diagnostics"):
        raise MessageNotSuccessfulError(incoming_diagnostics)

    supplier = message_body.get("supplier")
    fhir_json = message_body.get("fhir_json")
    operation_requested = message_body.get("operation_requested")

    # Send request to Imms FHIR API and return the imms_id
    function_map = {"CREATE": send_create_request, "UPDATE": send_update_request, "DELETE": send_delete_request}
    return function_map[operation_requested](controller, fhir_json=fhir_json, supplier=supplier)
