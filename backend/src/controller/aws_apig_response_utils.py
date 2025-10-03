"""Utility module providing helper functions for dealing with response formats for AWS API Gateway"""
import json
from typing import Optional


def create_response(
    status_code: int,
    body: Optional[dict | str] = None,
    headers: Optional[dict] = None
):
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
