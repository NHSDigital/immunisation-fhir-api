''' DynamoDB Methods '''

from fhir_api.interfaces.dynamodb.dynamodb_init import DynamoDB
from fhir_api.models.dynamodb.read_models import SnomedReadModel
from fhir_api.models.dynamodb.update_model import UpdateSnomedModel

dynamodb = DynamoDB()
SNOMED_TABLE = 'snomed_data'  # Possible ENV_VAR


class SnomedDynamoDBMethods:
    @staticmethod
    def create_snomed_record(data_input: UpdateSnomedModel) -> bool:
        ''' Create dynamodb document using DataInput Model provided '''
        status = False
        table = dynamodb.database.Table(SNOMED_TABLE)
        response = table.put_item(Item=data_input.dict())
        if response.get('ResponseMetadata').get('HTTPStatusCode') == 200:
            status = True
        return status

    @staticmethod
    def read_snomed_record(snomed_code: str) -> SnomedReadModel:
        ''' Read DynamoDB snomed table for specific code '''
        table = dynamodb.database.Table(SNOMED_TABLE)
        response = table.get_item(Key={'snomed_code': snomed_code})
        print(response)

        return SnomedReadModel(**response.get('Item'))

    @staticmethod
    def update_snomed_record(
        snomed_code: str, update_model: UpdateSnomedModel
    ) -> bool:
        ''' Update row from table '''
        status = False
        table = dynamodb.database.Table(SNOMED_TABLE)
        response = table.get_item(
            Key={"snomed_code": snomed_code})
        if item := response.get('Item'):
            item.update(update_model.dict())
            response = table.put_item(Item=item)
            status = True

        return status

    @staticmethod
    def delete_snomed_record(snomed_code: str) -> bool:
        ''' Logically delete row from table '''
        status = False
        table = dynamodb.database.Table(SNOMED_TABLE)
        response = table.delete_item(
            Key={"snomed_code": snomed_code})

        print(response)
        if response.get('ResponseMetadata').get('HTTPStatusCode') == 200:
            status = True
        return status
