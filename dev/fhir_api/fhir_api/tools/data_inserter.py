# flake8: noqa

import boto3
from boto3.dynamodb.conditions import Key, Attr
import json
import uuid
import datetime

from fhir_api.tools.data_faker import generate_record_data

DYNAMODB = 'dynamodb'

table_db = "fhir_api_test"
dynamodb =  boto3.resource(
            DYNAMODB,
            endpoint_url="http://localhost:8000",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-west-2"
        )

table = dynamodb.Table(table_db)
# data = generate_records()
# data['nhsNumber'] = str(46409800)
# table.put_item(Item=data)

data = []
for i in range(1000):
    patient, immunization = generate_record_data()
    data.append(patient)
    data.append(immunization)

with table.batch_writer() as batch:
    for i in data:
        batch.put_item(Item=i)

    # response = table.put_item(Item=record)
    # if response.get('ResponseMetadata').get('HTTPStatusCode') == 200:
            # status = True
            # print(f"PUT: {response.get('ResponseMetadata').get('HTTPStatusCode')}")
    # else:
        # print("\n\n\nFAILURE\n\n\n")

# Scans Cost more that queries but allow for more searchable criteria
# response = table.scan(FilterExpression=Attr('data.status').eq("not-done")) 
# for i in response.get('Items'):
    # print(i.get('fullUrl'))
    # print(i.get('nhsNumber'))

# Queries are cheaper but can only be done on GSI and PK
# response2 = table.query(KeyConditionExpression=Key("nhsNumber").eq("46409800"))
# print(f"QUERY:{response2}")

# collected_item = table.get_item(
    # Key={
        # "nhsNumber": str(46409800),
        # "fullUrl": 'urn:uuid:28c73376-0657-48da-b64d-dc6eb83f64f5'
    # }
# )
# print(collected_item['Item'])
# collected_item['Item']["dateModified"] = datetime.datetime.now().isoformat()
#response = table.put_item(Item=collected_item['Item'])

# response = table.scan(FilterExpression=Attr('data.recorded').gte("2022-08-25") & Attr("data.recorded").lte("9999-01-01"))
# print(response)