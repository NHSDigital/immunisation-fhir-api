''' DynamoDB Router Methods '''

from fastapi import APIRouter
from typing import Optional

from fhir_api.interfaces.dynamodb.immunisation import ImmunisationCRUDMethods
from fhir_api.models.dynamodb.data_input import (
    DataInput,
    SuccessModel
)
from fhir_api.models.dynamodb.update_model import UpdateImmunizationRecord

from fhir_api.models.dynamodb.read_models import BatchImmunizationRead

ENDPOINT = '/immunisation'
router = APIRouter(prefix=ENDPOINT)


@router.post(
    "",
    description="Create Method for Immunization Endpoint",
    tags=['Dynamodb', 'CRUD', 'Create'],
    response_model=SuccessModel
)
def create_immunization_record(data_input: DataInput) -> SuccessModel:
    return SuccessModel(
        success=ImmunisationCRUDMethods.create_immunization_record(
            data_input=data_input
            )
        )


@router.get(
    "",
    description="Read Method for Immunization Endpoint",
    tags=['Dynamodb', 'CRUD', 'Read'],
    response_model=BatchImmunizationRead
)
def read_immunization_record(
    nhsNumber: str,
    fullUrl: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = "9999-01-01",
    include_record: Optional[str] = None
) -> BatchImmunizationRead:
    return ImmunisationCRUDMethods.read_immunization_record(
        nhs_number=nhsNumber,
        full_url=fullUrl,
        from_date=from_date,
        to_date=to_date,
        include_record=include_record
    )


@router.put(
    "",
    description="Update Method for Immunization Endpoint",
    tags=['Dynamodb', 'CRUD', 'Delete'],
    response_model=SuccessModel
)
def update_immunization_record(nhsNumber: str, fullUrl: str, update_model: UpdateImmunizationRecord) -> SuccessModel:
    return SuccessModel(
        success=ImmunisationCRUDMethods.update_immunization_record(
            nhs_number=nhsNumber,
            full_url=fullUrl,
            update_model=update_model
        )
    )


@router.delete(
    "",
    description="Delete Method for Immunization Endpoint",
    tags=['Dynamodb', 'CRUD', 'Delete'],
    response_model=SuccessModel
)
def delete_immunization_record(nhsNumber: str, fullUrl: str) -> SuccessModel:
    return SuccessModel(
        success=ImmunisationCRUDMethods.delete_immunization_record(
            nhs_number=nhsNumber,
            full_url=fullUrl
        )
    )
