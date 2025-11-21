import argparse
import logging
import pprint

from controller.fhir_controller import FhirController, make_controller
from log_structure import function_info

logging.basicConfig(level="INFO")
logger = logging.getLogger()


@function_info
def delete_imms_handler(event, _context):
    return delete_immunization(event, make_controller())


def delete_immunization(event, controller: FhirController):
    return controller.delete_immunization(event)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("delete_imms_handler")
    parser.add_argument("id", help="Id of Immunization.", type=str)
    args = parser.parse_args()

    event = {
        "pathParameters": {"id": args.id},
        "headers": {
            "Content-Type": "application/x-www-form-urlencoded",
            "AuthenticationType": "ApplicationRestricted",
        },
    }
    pprint.pprint(delete_imms_handler(event, {}))
