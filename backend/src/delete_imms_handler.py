import argparse
import pprint
import uuid

from authorization import Permission
from fhir_controller import FhirController, make_controller
from models.errors import Severity, Code, create_operation_outcome
from log_structure import function_info
from constants import GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE

import logging

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")
logger.info("create_imms_handler.py")

@function_info
def delete_imms_handler(event, context):
    return delete_immunization(event, make_controller(logger=logger))


def delete_immunization(event, controller: FhirController):
    try:
        return controller.delete_immunization(event)
    except Exception:  # pylint: disable = broad-exception-caught
        exp_error = create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.server_error,
            diagnostics=GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE,
        )
        return FhirController.create_response(500, exp_error)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("delete_imms_handler")
    parser.add_argument("id", help="Id of Immunization.", type=str)
    args = parser.parse_args()

    event = {
        "pathParameters": {"id": args.id},
        "headers": {
            "Content-Type": "application/x-www-form-urlencoded",
            "AuthenticationType": "ApplicationRestricted",
            "Permissions": (",".join([Permission.DELETE])),
        },
    }
    pprint.pprint(delete_imms_handler(event, {}))
