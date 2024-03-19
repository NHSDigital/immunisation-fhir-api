import argparse
import pprint
import uuid

from fhir_controller import FhirController, make_controller
from local_lambda import load_string
from models.errors import Severity, Code, create_operation_outcome


def update_imms_handler(event, context):
    return update_imms(event, make_controller())


def update_imms(event, controller: FhirController):
    try:
        return controller.update_immunization(event)
    except Exception as e:
        exp_error = create_operation_outcome(resource_id=str(uuid.uuid4()), severity=Severity.error,
                                             code=Code.server_error,
                                             diagnostics=str(e))
        return FhirController.create_response(500, exp_error)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("update_imms_handler")
    parser.add_argument("id", help="Id of Immunization.", type=str)
    parser.add_argument("path", help="Path to Immunization JSON file.", type=str)
    args = parser.parse_args()

    event = {
        "pathParameters": {
            "id": args.id
        },
        "body": load_string(args.path)
    }

    pprint.pprint(event)
    pprint.pprint(update_imms_handler(event, {}))
