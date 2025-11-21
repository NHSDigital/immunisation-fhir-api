import argparse
import logging
import pprint

from controller.fhir_controller import FhirController, make_controller
from local_lambda import load_string
from log_structure import function_info

logging.basicConfig(level="INFO")
logger = logging.getLogger()


@function_info
def update_imms_handler(event, _context):
    return update_imms(event, make_controller())


def update_imms(event, controller: FhirController):
    return controller.update_immunization(event)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("update_imms_handler")
    parser.add_argument("id", help="Id of Immunization.", type=str)
    parser.add_argument("path", help="Path to Immunization JSON file.", type=str)
    args = parser.parse_args()

    event = {
        "pathParameters": {"id": args.id},
        "body": load_string(args.path),
        "headers": {
            "Content-Type": "application/x-www-form-urlencoded",
            "AuthenticationType": "ApplicationRestricted",
        },
    }

    pprint.pprint(event)
    pprint.pprint(update_imms_handler(event, {}))
