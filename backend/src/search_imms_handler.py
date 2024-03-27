import argparse
import json
import pprint
import traceback
import uuid

from aws_lambda_typing import context as context_, events

from authorization import Permission
from fhir_controller import FhirController, make_controller
from models.errors import Severity, Code, create_operation_outcome


def search_imms_handler(event: events.APIGatewayProxyEventV1, context: context_):
    return search_imms(event, make_controller())


def search_imms(event: events.APIGatewayProxyEventV1, controller: FhirController):
    try:
        return controller.search_immunizations(event)
    except Exception as e:
        exp_error = create_operation_outcome(resource_id=str(uuid.uuid4()),
                                             severity=Severity.error,
                                             code=Code.server_error,
                                             diagnostics=traceback.format_exc())
        return FhirController.create_response(500, exp_error)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("search_imms_handler")
    parser.add_argument(
        "--patient.identifier",
        help="Identifier of Patient",
        type=str,
        required=True,
        dest="patient_identifier")
    parser.add_argument(
        "--immunization.target",
        help="http://hl7.org/fhir/ValueSet/immunization-target-disease",
        type=str,
        required=True,
        nargs="+",
        dest="immunization_target")
    parser.add_argument(
        "--date.from",
        type=str,
        required=False,
        dest="date_from")
    parser.add_argument(
        "--date.to",
        type=str,
        required=False,
        dest="date_to")

    args = parser.parse_args()

    event: events.APIGatewayProxyEventV1 = {
        "multiValueQueryStringParameters": {
            "patient.identifier": [args.patient_identifier],
            "-immunization.target": [",".join(args.immunization_target)],
            "-date.from": [args.date_from] if args.date_from else [],
            "-date.to": [args.date_to] if args.date_to else [],
            "_include": ["Immunization:patient"]
        },
        "httpMethod": "POST",
        "headers": {
            'Content-Type': 'application/x-www-form-urlencoded',
            'AuthenticationType': 'ApplicationRestricted',
            'Permissions': (','.join([Permission.SEARCH]))
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
