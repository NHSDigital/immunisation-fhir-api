import argparse
import pprint
import uuid

from authorization import Permission
from fhir_controller import FhirController, make_controller
from models.errors import Severity, Code, create_operation_outcome


def get_imms_handler(event, context):
    return get_immunization_by_id(event, make_controller())


def get_immunization_by_id(event, controller: FhirController):
    try:
        return controller.get_immunization_by_id(event)
    except Exception as e:
        exp_error = create_operation_outcome(resource_id=str(uuid.uuid4()), severity=Severity.error,
                                             code=Code.server_error,
                                             diagnostics=str(e))
        return FhirController.create_response(500, exp_error)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("get_imms_handler")
    parser.add_argument("id", help="Id of Immunization.", type=str)
    args = parser.parse_args()

    event = {
        "pathParameters": {
            "id": args.id
        },
        "headers": {
            'Content-Type': 'application/x-www-form-urlencoded',
            'AuthenticationType': 'ApplicationRestricted',
            'Permissions': (','.join([Permission.READ]))
        }
    }
    pprint.pprint(get_imms_handler(event, {}))
