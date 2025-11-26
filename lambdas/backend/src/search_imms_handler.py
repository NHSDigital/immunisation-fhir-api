import argparse
import json
import pprint

from aws_lambda_typing.context import Context
from aws_lambda_typing.events import APIGatewayProxyEventV1

from controller.constants import SEARCH_IMMS_POST_PATH
from controller.fhir_controller import FhirController, make_controller
from log_structure import function_info


@function_info
def search_imms_handler(event: APIGatewayProxyEventV1, _context: Context):
    return search_imms(event, make_controller())


def search_imms(event: APIGatewayProxyEventV1, controller: FhirController):
    return controller.search_immunizations(event, is_post_endpoint_req=event.get("path") == SEARCH_IMMS_POST_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("search_imms_handler")
    parser.add_argument(
        "--patient.identifier",
        help="Identifier of Patient",
        type=str,
        required=True,
        dest="patient_identifier",
    )
    parser.add_argument(
        "--immunization.target",
        help="http://hl7.org/fhir/ValueSet/immunization-target-disease",  # NOSONAR(S5332)
        type=str,
        required=True,
        nargs="+",
        dest="immunization_target",
    )
    parser.add_argument("--date.from", type=str, required=False, dest="date_from")
    parser.add_argument("--date.to", type=str, required=False, dest="date_to")
    parser.add_argument(
        "--identifier",
        help="Identifier of System",
        type=str,
        required=False,
        dest="identifier",
    )
    parser.add_argument(
        "--elements",
        help="Identifier of System",
        type=str,
        required=False,
        dest="_elements",
    )
    args = parser.parse_args()

    event: APIGatewayProxyEventV1 = {
        "multiValueQueryStringParameters": {
            "patient.identifier": [args.patient_identifier],
            "-immunization.target": [",".join(args.immunization_target)],
            "-date.from": [args.date_from] if args.date_from else [],
            "-date.to": [args.date_to] if args.date_to else [],
            "_include": ["Immunization:patient"],
            "identifier": ([args.immunization_identifier] if args.immunization_identifier else []),
            "_elements": [args._element] if args._element else [],
        },
        "httpMethod": "POST",
        "headers": {
            "Content-Type": "application/x-www-form-urlencoded",
            "AuthenticationType": "ApplicationRestricted",
        },
        "body": None,
        "resource": None,
        "isBase64Encoded": None,
        "multiValueHeaders": None,
        "path": None,
        "pathParameters": None,
        "queryStringParameters": None,
        "requestContext": None,
    }

    result = search_imms_handler(event, {})
    if "body" in result:
        print(json.dumps(json.loads(result["body"]), indent=2))
    else:
        pprint.pprint(result)
