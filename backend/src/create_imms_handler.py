import argparse
import pprint
import uuid

from authorization import Permission
from fhir_controller import FhirController, make_controller
from local_lambda import load_string
from models.errors import Severity, Code, create_operation_outcome
from log_structure import function_info


@function_info
def create_imms_handler(event, context):
    return create_immunization(event, make_controller())


def create_immunization(event, controller: FhirController):
    try:
        return controller.create_immunization(event)
    except Exception as e:
        exp_error = create_operation_outcome(
            resource_id=str(uuid.uuid4()), severity=Severity.error, code=Code.server_error, diagnostics=str(e)
        )
        return FhirController.create_response(500, exp_error)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("create_imms_handler")
    parser.add_argument("path", help="Path to Immunization JSON file.", type=str)
    args = parser.parse_args()

    event = {
        "body": load_string(args.path),
        "headers": {
            "Content-Type": "application/x-www-form-urlencoded",
            "AuthenticationType": "ApplicationRestricted",
            "Permissions": (",".join([Permission.CREATE])),
        },
    }

    pprint.pprint(event)
    pprint.pprint(create_imms_handler(event, {}))
