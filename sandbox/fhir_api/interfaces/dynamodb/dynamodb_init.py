#!/usr/bin/env python
""" Initialise mongodb connection """
import os

import boto3


DYNAMODB = 'dynamodb'

class DynamoDBSettings:
    ''' Class to store DynamoDB env-vars'''
    host: str = os.getenv('DYNAMODB_HOST')
    port: str = os.getenv('DYNAMODB_PORT')
    access_key: str = os.getenv('AWS_ACCESS_KEY')
    secret_key: str = os.getenv('AWS_SECRET_KEY')
    region: str = os.getenv("AWS_REGION_NAME")
    uri: str = f"http://{host}:{port}"

class DynamoDB:
    ''' Class to interact with DynamoDB '''

    def __init__(self):
        self.database = boto3.resource(
            DYNAMODB,
            endpoint_url=DynamoDBSettings.uri,
            aws_access_key_id=DynamoDBSettings.access_key,
            aws_secret_access_key=DynamoDBSettings.secret_key,
            region_name=DynamoDBSettings.region
        )
