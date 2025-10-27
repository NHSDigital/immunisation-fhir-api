import argparse
import logging
import pprint

from controller.fhir_controller import FhirController, make_controller
from local_lambda import load_string
from log_structure import function_info

logging.basicConfig(level="INFO")
logger = logging.getLogger()


@function_info
def create_imms_handler(event, _context):
    return create_immunization(event, make_controller())


def create_immunization(event, controller: FhirController):
    return controller.create_immunization(event)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("create_imms_handler")
    parser.add_argument("path", help="Path to Immunization JSON file.", type=str)
    args = parser.parse_args()

    event = {
        "body": load_string(args.path),
        "headers": {
            "Content-Type": "application/x-www-form-urlencoded",
            "AuthenticationType": "ApplicationRestricted",
        },
    }

    pprint.pprint(event)
    pprint.pprint(create_imms_handler(event, {}))
