from datetime import datetime
from utils.base_test import ImmunizationBaseTest
from utils.immunisation_api import parse_location
from utils.resource import generate_imms_resource, get_dynamodb_table
import time
import copy
import os


class TestDeltaImmunization(ImmunizationBaseTest):

    CREATE_OPERATION = "CREATE"
    UPDATE_OPERATION = "UPDATE"
    DELETE_OPERATION = "DELETE"
    DPS_SOURCE = "DPS"

    def test_create_delta_imms(self):
        """Should create,update,delete FHIR Immunization resource causing those resources to be stored in Delta table"""
        imms_delta_table = get_dynamodb_table(os.getenv("IMMS_DELTA_TABLE_NAME"))
        # Given
        start_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        # Creating two Imms Event, one of them will be updated and second of them will be deleted afterwards
        # It should add 4 rows in Delta Storage table
        create_update_imms = generate_imms_resource()
        create_delete_imms = generate_imms_resource()
        create_update_response = self.default_imms_api.create_immunization(create_update_imms)

        create_delete_response = self.default_imms_api.create_immunization(create_delete_imms)
        assert create_update_response.status_code == 201
        assert create_delete_response.status_code == 201
        create_update_imms_id = parse_location(create_update_response.headers["Location"])

        create_delete_imms_id = parse_location(create_delete_response.headers["Location"])

        # When
        update_payload = copy.deepcopy(create_update_imms)
        update_payload["id"] = create_update_imms_id
        update_payload["location"]["identifier"]["value"] = "Y11111"
        create_update_response = self.default_imms_api.update_immunization(create_update_imms_id, update_payload)
        self.assertEqual(create_update_response.status_code, 200)

        create_delete_response = self.default_imms_api.delete_immunization(create_delete_imms_id)
        self.assertEqual(create_delete_response.status_code, 204)

        # Then
        # Adding a delay of 30 seconds, because lambda can take some time to put records in Delta table
        time.sleep(30)
        end_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        operations = [
            self.CREATE_OPERATION,
            self.DELETE_OPERATION,
            self.UPDATE_OPERATION,
        ]
        delta_imms_query_response = []
        for operation in operations:
            expression_attribute_values = {
                ":start": start_timestamp,
                ":end": end_timestamp,
                ":operation": operation,
                ":DPS": self.DPS_SOURCE,
            }

            key_condition_expression = "Operation = :operation AND DateTimeStamp BETWEEN :start AND :end "
            expression_attribute_names = {"#Source": "Source"}  # Define an alias for the reserved attribute name
            is_not_DPS = "#Source <> :DPS"
            response = imms_delta_table.query(
                IndexName="SearchIndex",
                KeyConditionExpression=key_condition_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ExpressionAttributeNames=expression_attribute_names,
                FilterExpression=is_not_DPS,
            )
            delta_imms_query_response.extend((entity["ImmsID"], entity["Operation"]) for entity in response["Items"])
        if operation == self.CREATE_OPERATION:
            self.assertTrue(
                ((create_update_imms_id, self.CREATE_OPERATION) in delta_imms_query_response)
                and ((create_delete_imms_id, self.CREATE_OPERATION) in delta_imms_query_response)
            )
        elif operation == self.UPDATE_OPERATION:
            self.assertTrue((create_update_imms_id, self.UPDATE_OPERATION) in delta_imms_query_response)
        elif operation == self.DELETE_OPERATION:
            self.assertTrue((create_delete_imms_id, self.DELETE_OPERATION) in delta_imms_query_response)
