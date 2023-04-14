''' Table Router Methods '''

from fastapi import APIRouter

from fhir_api.interfaces.dynamodb.immunisation import ImmunisationCRUDMethods

ENDPOINT = '/tables'
router = APIRouter(prefix=ENDPOINT)


@router.get(
    "",
    description="List all DynamoDB tables",
    tags=['DynamoDB', 'Tables']
)
def list_tables():
    ''' List tables in DynamoDB Endpoint '''
    return ImmunisationCRUDMethods.list_tables()
