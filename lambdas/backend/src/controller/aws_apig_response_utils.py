"""Utility module providing helper functions for dealing with response formats for AWS API Gateway"""

import json


def create_response(status_code: int, body: dict | str | None = None, headers: dict | None = None) -> dict:
    """Creates response body as per Lambda -> API Gateway proxy integration"""
    if body is not None:
        if isinstance(body, dict):
            body = json.dumps(body)
        if headers:
            headers["Content-Type"] = "application/fhir+json"
        else:
            headers = {"Content-Type": "application/fhir+json"}

    return {
        "statusCode": status_code,
        "headers": headers if headers else {},
        **({"body": body} if body else {}),
    }
