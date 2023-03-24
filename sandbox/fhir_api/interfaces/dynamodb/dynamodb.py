''' DynamoDB Methods '''

from datetime import datetime
from typing import Optional

from boto3.dynamodb.conditions import Key, Attr

from fhir_api.interfaces.dynamodb.dynamodb_init import DynamoDB
from fhir_api.models.dynamodb.table import CreateTable
from fhir_api.models.dynamodb.data_input import DataInput
from fhir_api.models.dynamodb.read_models import BatchImmunizationRead, Resource
from fhir_api.models.dynamodb.update_model import UpdateImmunizationRecord
from fhir_api.models.fhir_r4.immunization import Immunization
from fhir_api.tools.utils import generate_fullurl

dynamodb = DynamoDB()
IMMUNIZATION_TABLE = 'fhir_api_test' # Possible ENV_VAR

class DynamoDBMethods:
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
    @staticmethod
    def create_immunization_record(data_input: DataInput) -> bool:
        ''' Create dynamodb document using DataInput Model provided '''
        status = False
        table = dynamodb.database.Table(IMMUNIZATION_TABLE)
        data_input = data_input.dict()
        data_input['fullUrl'] = generate_fullurl()
        date_modified = datetime.now().isoformat()
        data_input['dateModified'] = date_modified
        response = table.put_item(Item=data_input)
        if response.get('ResponseMetadata').get('HTTPStatusCode') == 200:
            status = True
        return status

    @staticmethod
    def read_immunization_record(
        nhs_number: str,
        full_url: Optional[str],
        from_date: Optional[str] = None,
        to_date: Optional[str] = "9999-01-01",
        include_record: Optional[str] = None
    ) -> BatchImmunizationRead:
        ''' Read DynamoDB table for immunization records '''
        def create_resource(item, mode):
            resource = {}
            resource['fullUrl'] = item.get('fullUrl')
            resource['resource'] = Immunization(**item.get('data'))
            resource['search'] = {'mode': mode}
            return resource

        if not include_record:
            filter_expression = Attr("entityType").eq('immunization')

        batch = {}
        batch['entry'] = []
        table = dynamodb.database.Table(IMMUNIZATION_TABLE)

        if full_url:
            batch['type'] = 'targeted'
            response = table.get_item(Key={
                'nhsNumber': nhs_number,
                'fullUrl': full_url
            })
            data = create_resource(response.get('Item'), mode='query')
            batch['total'] = 1
            batch['entry'].append(Resource(**data))
        else:
            filter_expression = filter_expression &\
                Attr('nhsNumber').eq(nhs_number) &\
                Attr('data.recorded').gte(from_date) &\
                Attr("data.recorded").lte(to_date)

            batch['type'] = 'searchset'
            if from_date:
                response = table.scan(
                FilterExpression=filter_expression)
            else:
                response = table.query(
                    KeyConditionExpression=Key("nhsNumber").eq(nhs_number),
                    FilterExpression=filter_expression
                )

            batch['total'] = len(response.get('Items'))

            for i in response.get('Items'):
                resource = create_resource(i, mode='scan')
                batch['entry'].append(Resource(**resource))


        batch_model = BatchImmunizationRead(**batch)
        return batch_model

    @staticmethod
    def update_immunization_record(
        nhs_number: str, full_url: str, update_model: UpdateImmunizationRecord
        ) -> bool:
        ''' Update row from table '''
        status = False
        table = dynamodb.database.Table(IMMUNIZATION_TABLE)
        modified_date = datetime.now().isoformat()
        response = table.get_item(Key={"nhsNumber": str(nhs_number), "fullUrl": full_url})
        if item := response.get('Item'):
            item['data'].update(update_model.dict())
            item["dateModified"] = modified_date
            response = table.put_item(Item=item)
            status = True

        return status

    @staticmethod
    def delete_immunization_record(nhs_number: str, full_url: str) -> bool:
        ''' Logically delete row from table '''
        status = False
        table = dynamodb.database.Table(IMMUNIZATION_TABLE)
        deleted_date = datetime.now().isoformat()
        response = table.get_item(Key={"nhsNumber": str(nhs_number), "fullUrl": full_url})

        if item := response.get('Item'):
            item["dateModified"] = item['dateDeleted'] = deleted_date
            response = table.put_item(Item=item)
            status = True

        return status



