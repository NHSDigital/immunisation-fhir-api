import json
import sys

import boto3

sample_file = "sample_data/2023-11-29T19:04:37_immunisation-30.json"

dynamodb_url = "http://localhost:4566"
table_name = "imms-default-imms-events"


class DynamoTable:
    def __init__(self, endpoint_url, _table_name):
        db = boto3.resource('dynamodb', endpoint_url=endpoint_url, region_name="us-east-1")
        self.table = db.Table(_table_name)

    def create_immunization(self, immunization):
        # When seeding, we preserve the original ID, instead of creating new one
        new_id = immunization["id"]
        patient_id = immunization["patient"]["identifier"]["value"]
        disease_type = immunization["protocolApplied"][0]["targetDisease"][0]["coding"][0]["code"]

        patient_sk = f"{disease_type}#{new_id}"

        response = self.table.put_item(Item={
            'PK': self._make_immunization_pk(new_id),
            'Resource': json.dumps(immunization),
            'PatientPK': self._make_patient_pk(patient_id),
            'PatientSK': patient_sk,
            'Version': 1
        })

        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            return immunization
        else:
            raise Exception("Non-200 response from dynamodb")

    @staticmethod
    def _make_immunization_pk(_id: str):
        return f"Immunization#{_id}"

    @staticmethod
    def _make_patient_pk(_id: str):
        return f"Patient#{_id}"


def seed_immunization(table, _sample_file):
    with open(_sample_file, "r") as raw_data:
        imms_list = json.loads(raw_data.read())

    for imms in imms_list:
        table.create_immunization(imms)

    print(f"{len(imms_list)} resources added successfully")


if __name__ == '__main__':
    _table = DynamoTable(dynamodb_url, table_name)

    seed_file = sample_file
    if len(sys.argv) > 1:
        seed_file = sys.argv[1]

    seed_immunization(_table, seed_file)
