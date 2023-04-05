''' DynamoDB Router Methods '''

from fastapi import APIRouter

from fhir_api.interfaces.dynamodb.snomed import SnomedDynamoDBMethods
from fhir_api.models.dynamodb.read_models import SnomedReadModel
from fhir_api.models.dynamodb.update_model import UpdateSnomedModel
from fhir_api.models.dynamodb.data_input import SuccessModel

ENDPOINT = '/snomed'
router = APIRouter(prefix=ENDPOINT)


@router.post(
    "",
    description="Create Method for snomed Endpoint",
    tags=['Snomed', 'DynamoDB'],
    response_model=SuccessModel,
)
def create_snomed_record(data_input: UpdateSnomedModel) -> SuccessModel:
    return SuccessModel(
        success=SnomedDynamoDBMethods.create_snomed_record(
            data_input=data_input
        )
    )


@router.get(
    "",
    description="List all Snomed Entries",
    tags=['Snomed', 'DynamoDB'],
    response_model=SnomedReadModel
)
def snomed_get(snomed_code: str) -> dict:
    return SnomedDynamoDBMethods.read_snomed_record(snomed_code=snomed_code)


@router.put(
    "",
    description="Update Method for snomed Endpoint",
    tags=['Snomed', 'DynamoDB'],
    response_model=SuccessModel
)
def update_snomed_record(snomed_code: str, update_model: UpdateSnomedModel) -> SuccessModel:
    return SuccessModel(
        success=SnomedDynamoDBMethods.update_snomed_record(
            snomed_code=snomed_code,
            update_model=update_model
        )
    )


@router.delete(
    "",
    description="Delete Method for snomed Endpoint",
    tags=['Snomed', 'DynamoDB'],
    response_model=SuccessModel
)
def delete_snomed_record(snomed_code: str) -> SuccessModel:
    return SuccessModel(
        success=SnomedDynamoDBMethods.delete_snomed_record(
            snomed_code=snomed_code,
        )
    )
