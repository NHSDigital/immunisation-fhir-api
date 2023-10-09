import json


def handler(event, context):
    response = {
        "statusCode": 404,  # HTTP status code
        "headers": {
            "Content-Type": "application/json",  # Specify the content type
        },
        "body": json.dumps({
            "resourceType": "OperationOutcome",
            "id": "a5abca2a-4eda-41da-b2cc-95d48c6b791d",
            "meta": {
                "profile": [
                    "https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"
                ]
            },
            "issue": [
                {
                    "severity": "error",
                    "code": "not-found",
                    "details": {
                        "coding": [
                            {
                                "system": "https://fhir.nhs.uk/Codesystem/http-error-codes",
                                "code": "NOT_FOUND"
                            }
                        ]
                    },
                    "diagnostics": "The requested resource was not found."
                }
            ]
        })
    }

    return response
