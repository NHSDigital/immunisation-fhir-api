import argparse
import logging
import pprint
import uuid

from constants import GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE
from fhir_controller import FhirController, make_controller
from local_lambda import load_string
from log_structure import function_info
from models.errors import Code, Severity, create_operation_outcome

logging.basicConfig(level="INFO")
logger = logging.getLogger()


@function_info
def update_imms_handler(event, _context):
    return update_imms(event, make_controller())


def update_imms(event, controller: FhirController):
    try:
        return controller.update_immunization(event)
    except Exception:  # pylint: disable = broad-exception-caught
        logger.exception("Unhandled exception")
        exp_error = create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.server_error,
            diagnostics=GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE,
        )
        return FhirController.create_response(500, exp_error)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("update_imms_handler")
    parser.add_argument("id", help="Id of Immunization.", type=str)
    parser.add_argument("path", help="Path to Immunization JSON file.", type=str)
    args = parser.parse_args()

    event = {
        "pathParameters": {"id": args.id},
        "body": load_string(args.path),
        "headers": {"Content-Type": "application/x-www-form-urlencoded", "AuthenticationType": "ApplicationRestricted"},
    }

    pprint.pprint(event)
    pprint.pprint(update_imms_handler(event, {}))
