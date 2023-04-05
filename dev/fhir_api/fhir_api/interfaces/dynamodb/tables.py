''' Tables DynamoDB Methods '''

from fhir_api.interfaces.dynamodb.dynamodb_init import DynamoDB
from fhir_api.models.dynamodb.table import CreateTable

dynamodb = DynamoDB()


class TablesCRUDMethods:
    @staticmethod
    def list_tables() -> list:
        ''' Query DynamoDB and return list of available tables '''
        return {"tables": [i.name for i in list(dynamodb.database.tables.all())]}

    @staticmethod
    def create_table(create: CreateTable) -> list:
        ''' Create table in dynamodb '''
        table = dynamodb.database.create_table(
            TableName=create.table_name,
            KeySchema=[i.dict() for i in create.key_schema],
            AttributeDefinitions=[i.dict() for i in create.attribute_definition],
            ProvisionedThroughput=create.provisioned_throughput.dict(),
        )

        table.wait_until_exists()

        return {"tables": [i.name for i in list(dynamodb.database.tables.all())]}

    # @staticmethod
    # def getter(table_name: str, _pk: Optional[str] = None) -> list:
        # ''' Scan table and return all results '''
        # table = dynamodb.database.Table(table_name)
#
        # if _pk:
        # response = table.scan(FilterExpression=Attr('PK').eq(_pk))
        # else:
        # response = table.scan()
#
        # data = response['Items']
#
        # while 'LastEvaluatedKey' in response:
        # response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        # data.extend(response['Items'])
        #
        # return data