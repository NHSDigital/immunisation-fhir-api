import argparse
import json
import logging
import pprint
import uuid

from aws_lambda_typing import context as context_, events


from fhir_controller import FhirController, make_controller
from models.errors import Severity, Code, create_operation_outcome
from constants import GENERIC_SERVER_ERROR_DIAGNOSTICS_MESSAGE
from log_structure import function_info
from search_parameter_validator import (
    is_immunization_by_identifier,
    get_parsed_body
)

logging.basicConfig(level="INFO")
logger = logging.getLogger()

@function_info
def search_imms_handler(event: events.APIGatewayProxyEventV1, _context: context_):
    return search_imms(event, make_controller())


def search_imms(event: events.APIGatewayProxyEventV1, controller: FhirController):
    try:

        query_params = event.get("queryStringParameters", {})
        body = event.get("body")
        has_body = body is not None
        has_query_params = query_params is not None and query_params != {}
        if has_query_params or has_body:
            if is_immunization_by_identifier(query_params, get_parsed_body(body)):
                return controller.get_immunization_by_identifier(event)
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
            
    except ValueError as ve:
        logger.exception("ValueError occurred")
        exp_error = create_operation_outcome(
            resource_id=str(uuid.uuid4()),
            severity=Severity.error,
            code=Code.invalid,
            diagnostics=str(ve)
        )
        return FhirController.create_response(400, exp_error)
    except Exception:  # pylint: disable = broad-exception-caught
        logger.exception("Unhandled exception")
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
        "--identifier",
        help="Identifier of System",
        type=str,
        required=False,
        dest="identifier",
    )
    parser.add_argument("--elements", help="Identifier of System", type=str, required=False, dest="_elements")
    args = parser.parse_args()

    event: events.APIGatewayProxyEventV1 = {
        "multiValueQueryStringParameters": {
            "patient.identifier": [args.patient_identifier],
            "-immunization.target": [",".join(args.immunization_target)],
            "-date.from": [args.date_from] if args.date_from else [],
            "-date.to": [args.date_to] if args.date_to else [],
            "_include": ["Immunization:patient"],
            "identifier": [args.immunization_identifier] if args.immunization_identifier else [],
            "_elements": [args._element] if args._element else [],
        },
        "httpMethod": "POST",
        "headers": {
            "Content-Type": "application/x-www-form-urlencoded",
            "AuthenticationType": "ApplicationRestricted"
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
