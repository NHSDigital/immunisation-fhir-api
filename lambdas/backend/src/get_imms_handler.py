import argparse
import logging
import pprint

from controller.fhir_controller import FhirController, make_controller
from log_structure import function_info

logging.basicConfig(level="INFO")
logger = logging.getLogger()


@function_info
def get_imms_handler(event, _context):
    return get_immunization_by_id(event, make_controller())


def get_immunization_by_id(event, controller: FhirController):
    return controller.get_immunization_by_id(event)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("get_imms_handler")
    parser.add_argument("id", help="Id of Immunization.", type=str)
    args = parser.parse_args()

    event = {
        "pathParameters": {"id": args.id},
        "headers": {
            "Content-Type": "application/x-www-form-urlencoded",
            "AuthenticationType": "ApplicationRestricted",
        },
    }
    pprint.pprint(get_imms_handler(event, {}))
