''' DynamoDB Methods '''

from datetime import datetime
from typing import Optional

from boto3.dynamodb.conditions import Key, Attr

from fhir_api.interfaces.dynamodb.dynamodb_init import DynamoDB
from fhir_api.models.dynamodb.data_input import DataInput
from fhir_api.models.dynamodb.read_models import BatchImmunizationRead, Resource
from fhir_api.models.dynamodb.update_model import UpdateImmunizationRecord
from fhir_api.models.fhir_r4.immunization import Immunization
from fhir_api.models.fhir_r4.patient import Patient
from fhir_api.tools.utils import generate_fullurl

dynamodb = DynamoDB()
IMMUNIZATION_TABLE = 'fhir_api_test'  # Possible ENV_VAR

MATCH = 'match'
INCLUDE = 'include'


def create_resource(item, model, mode) -> dict:
    resource = {}
    resource['fullUrl'] = item.get('fullUrl')
    resource['resource'] = model(**item.get('data'))
    resource['search'] = {'mode': mode}
    return resource

class ImmunisationCRUDMethods:
    @staticmethod
    def create_immunization_record(data_input: DataInput) -> bool:
        ''' Create dynamodb document using DataInput Model provided '''
        status = False
        table = dynamodb.database.Table(IMMUNIZATION_TABLE)
        data_input = data_input.dict()
        data_input['fullUrl'] = generate_fullurl()
        date_modified = datetime.now().isoformat()
        data_input['dateModified'] = date_modified
        data_input['dieseaseType'] = data_input.data
        response = table.put_item(Item=data_input)
        if response.get('ResponseMetadata').get('HTTPStatusCode') == 200:
            status = True
        return status

    @staticmethod
    def query_index(nhsNumber: str, index_name: str, key: str, value: str) -> BatchImmunizationRead:
        ''' Query index for nhsNumber '''
        table = dynamodb.database.Table(IMMUNIZATION_TABLE)
        response = table.query(
            IndexName=index_name,
            KeyConditionExpression=Key(key).eq(value),
            FilterExpression=Attr('nhsNumber').eq(nhsNumber)
        )
        batch = {}
        batch['entry'] = []
        batch['total'] = len(response.get('Items'))
        batch['type'] = 'searchset'
        for i in response.get('Items'):
            resource = create_resource(i, model=Immunization, mode=MATCH)
            batch['entry'].append(Resource(**resource))

        batch_model = BatchImmunizationRead(**batch)

        return batch_model

    @staticmethod
    def read_immunization_record(
        nhs_number: str,
        full_url: Optional[str],
        from_date: Optional[str] = None,
        to_date: Optional[str] = "9999-01-01",
        include_record: Optional[str] = None
    ) -> BatchImmunizationRead:
        ''' Read DynamoDB table for immunization records '''

        if not include_record:
            filter_expression = Attr("entityType").eq('immunization')

        batch = {}
        batch['entry'] = []
        table = dynamodb.database.Table(IMMUNIZATION_TABLE)

        if full_url:
            batch['type'] = 'searchset'
            immunisation_response = table.get_item(Key={
                'nhsNumber': nhs_number,
                'fullUrl': full_url,
            })

            immunisation_data = create_resource(immunisation_response.get('Item'),
                                                model=Immunization,
                                                mode=MATCH)
            batch['total'] = 1
            batch['entry'].append(Resource(**immunisation_data))
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
                resource = create_resource(i, model=Immunization, mode=MATCH)
                batch['entry'].append(Resource(**resource))

        if include_record == "Immunization:patient":
            patient_response = table.query(KeyConditionExpression=Key("nhsNumber").eq(nhs_number),
                                           FilterExpression=Attr('entityType').eq('patient'))
            patient_data = create_resource(
                patient_response.get('Items')[0],
                model=Patient,
                mode=INCLUDE
            )
            batch['entry'].append(Resource(**patient_data))

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
        response = table.get_item(
            Key={"nhsNumber": str(nhs_number), "fullUrl": full_url})
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
        response = table.get_item(
            Key={"nhsNumber": str(nhs_number), "fullUrl": full_url})

        if item := response.get('Item'):
            item["dateModified"] = item['dateDeleted'] = deleted_date
            response = table.put_item(Item=item)
            status = True

        return status
