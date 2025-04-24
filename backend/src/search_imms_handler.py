import argparse
import json
import pprint
import traceback
import uuid

from aws_lambda_typing import context as context_, events

from authorization import Permission
from fhir_controller import FhirController, make_controller
from models.errors import Severity, Code, create_operation_outcome
from constants import GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE
from log_structure import function_info
import base64
import urllib.parse


@function_info
def search_imms_handler(event: events.APIGatewayProxyEventV1, context: context_):
    return search_imms(event, make_controller())


def search_imms(event: events.APIGatewayProxyEventV1, controller: FhirController):
    try:
        query_params = event.get("queryStringParameters", {})
        body = event["body"]
        body_has_immunization_identifier = False
        query_string_has_immunization_identifier = False
        query_string_has_element = False
        body_has_immunization_element = False
        if not (query_params == None and body == None):
            if query_params:
                query_string_has_immunization_identifier = (
                    "immunization.identifier" in event.get("queryStringParameters", {})
                )
                query_string_has_element = "_element" in event.get(
                    "queryStringParameters", {}
                )
            # Decode body from base64
            if event["body"]:
                decoded_body = base64.b64decode(event["body"]).decode("utf-8")
                # Parse the URL encoded body
                parsed_body = urllib.parse.parse_qs(decoded_body)

                # Check for 'immunization.identifier' in body
                body_has_immunization_identifier = (
                    "immunization.identifier" in parsed_body
                )
                body_has_immunization_element = "_element" in parsed_body
            if (
                query_string_has_immunization_identifier
                or body_has_immunization_identifier
                or query_string_has_element
                or body_has_immunization_element
            ):
                return controller.get_immunization_by_identifier(event)
            response = controller.search_immunizations(event)
        else:
            response = controller.search_immunizations(event)

        result_json = json.dumps(response)
        result_size = len(result_json.encode("utf-8"))

        if result_size > 6 * 1024 * 1024:
            exp_error = create_operation_outcome(
                resource_id=str(uuid.uuid4()),
                severity=Severity.error,
                code=Code.invalid,
                diagnostics="Search returned too many results. Please narrow down the search",
            )
            return FhirController.create_response(400, exp_error)
        return response
    except Exception:  # pylint: disable = broad-exception-caught
        exp_error = create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.server_error,
            diagnostics=GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE,
        )
        return FhirController.create_response(500, exp_error)


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
        help="http://hl7.org/fhir/ValueSet/immunization-target-disease",
        type=str,
        required=True,
        nargs="+",
        dest="immunization_target",
    )
    parser.add_argument("--date.from", type=str, required=False, dest="date_from")
    parser.add_argument("--date.to", type=str, required=False, dest="date_to")
    parser.add_argument(
        "--immunization.identifier",
        help="Identifier of System",
        type=str,
        required=False,
        dest="immunization_identifier",
    )
    parser.add_argument(
        "--element",
        help="Identifier of System",
        type=str,
        required=False,
        dest="_element",
    )
    args = parser.parse_args()

    event: events.APIGatewayProxyEventV1 = {
        "multiValueQueryStringParameters": {
            "patient.identifier": [args.patient_identifier],
            "-immunization.target": [",".join(args.immunization_target)],
            "-date.from": [args.date_from] if args.date_from else [],
            "-date.to": [args.date_to] if args.date_to else [],
            "_include": ["Immunization:patient"],
            "immunization_identifier": (
                [args.immunization_identifier] if args.immunization_identifier else []
            ),
            "_element": [args._element] if args._element else [],
        },
        "httpMethod": "POST",
        "headers": {
            "Content-Type": "application/x-www-form-urlencoded",
            "AuthenticationType": "ApplicationRestricted",
            "Permissions": (",".join([Permission.SEARCH])),
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
