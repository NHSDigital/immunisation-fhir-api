''' DynamoDB Router Methods '''

import json

from fastapi import APIRouter
from typing import Optional

from fhir_api.models.dynamodb.read_models import BatchImmunizationRead

ENDPOINT='/dynamodb'
router = APIRouter(prefix=ENDPOINT)

@router.get(
    "/Immunization",
    description="Read Method for Immunization Endpoint",
    tags=['Dynamodb', 'CRUD', 'Read'],
    response_model=BatchImmunizationRead
)
def read_immunization_record(
    nhsNumber: str,
    fullUrl: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = "9999-01-01",
    include_record: Optional[str] = None) -> BatchImmunizationRead:

    with open("/sandbox/fhir_api/sandbox_data.json", "r") as input:
        data = json.load(input)

    return BatchImmunizationRead(**data)
