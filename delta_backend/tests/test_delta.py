import unittest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
import os

# Set environment variables before importing the module
os.environ["AWS_SQS_QUEUE_URL"] = (
    "https://sqs.us-east-1.amazonaws.com/123456789012/MyQueue"
)
os.environ["DELTA_TABLE_NAME"] = "my_delta_table"
os.environ["SOURCE"] = "my_source"

from src.delta import (  # noqa: E402
    send_message,
    handler,
)  # Import after setting environment variables
import json  # noqa: E402


class DeltaTestCase(unittest.TestCase):

    def setUp(self):
        # Common setup if needed
        self.context = {}

    @staticmethod
    def setup_mock_sqs(
        mock_boto_client, return_value={"ResponseMetadata": {"HTTPStatusCode": 200}}
    ):
        mock_sqs = mock_boto_client.return_value
        mock_sqs.send_message.return_value = return_value
        return mock_sqs

    @staticmethod
    def setup_mock_dynamodb(mock_boto_resource, status_code=200):
        mock_dynamodb = mock_boto_resource.return_value
        mock_table = mock_dynamodb.Table.return_value
        mock_table.put_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": status_code}
        }
        return mock_table

    def setUp_mock_resources(self, mock_boto_resource, mock_boto_client):
        mock_dynamodb = mock_boto_resource.return_value
        mock_table = mock_dynamodb.Table.return_value
        mock_boto_client.return_value = {"key": "value"}
        mock_table.put_item.side_effect = Exception("Test Exception")
        return mock_table

    @staticmethod
    def get_event(event_name="INSERT", operation="CREATE", supplier="EMIS"):
        if operation != "DELETE":
            return {
                "Records": [
                    {
                        "eventName": event_name,
                        "dynamodb": {
                            "ApproximateCreationDateTime": 1690896000,
                            "NewImage": {
                                "PK": {"S": "covid#12345"},
                                "PatientSK": {"S": "covid#12345"},
                                "IdentifierPK": {"S": "system#1"},
                                "Operation": {"S": operation},
                                "SupplierSystem": {"S": supplier},
                                "Resource": {
                                    "S": '{"resourceType": "Immunization", "contained": [{"resourceType": "Practitioner", "id": "Pract1", "name": [{"family": "O\'Reilly", "given": ["Ellena"]}]}, {"resourceType": "Patient", "id": "Pat1", "identifier": [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9674963871"}], "name": [{"family": "GREIR", "given": ["SABINA"]}], "gender": "female", "birthDate": "2019-01-31", "address": [{"postalCode": "GU14 6TU"}]}], "extension": [{"url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure", "valueCodeableConcept": {"coding": [{"system": "http://snomed.info/sct", "code": "1303503001", "display": "Administration of vaccine product containing only Human orthopneumovirus antigen (procedure)"}]}}], "identifier": [{"system": "https://www.ravs.england.nhs.uk/", "value": "0001_RSV_v5_RUN_2_CDFDPS-742_valid_dose_1"}], "status": "completed", "vaccineCode": {"coding": [{"system": "http://snomed.info/sct", "code": "42605811000001109", "display": "Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd) (product)"}]}, "patient": {"reference": "#Pat1"}, "occurrenceDateTime": "2024-06-10T18:33:25+00:00", "recorded": "2024-06-10T18:33:25+00:00", "primarySource": true, "manufacturer": {"display": "Pfizer"}, "location": {"type": "Location", "identifier": {"value": "J82067", "system": "https://fhir.nhs.uk/Id/ods-organization-code"}}, "lotNumber": "RSVTEST", "expirationDate": "2024-12-31", "site": {"coding": [{"system": "http://snomed.info/sct", "code": "368208006", "display": "Left upper arm structure (body structure)"}]}, "route": {"coding": [{"system": "http://snomed.info/sct", "code": "78421000", "display": "Intramuscular route (qualifier value)"}]}, "doseQuantity": {"value": 0.5, "unit": "Milliliter (qualifier value)", "system": "http://unitsofmeasure.org", "code": "258773002"}, "performer": [{"actor": {"reference": "#Pract1"}}, {"actor": {"type": "Organization", "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "X0X0X"}}}], "reasonCode": [{"coding": [{"code": "Test", "system": "http://snomed.info/sct"}]}], "protocolApplied": [{"targetDisease": [{"coding": [{"system": "http://snomed.info/sct", "code": "840539006", "display": "Disease caused by severe acute respiratory syndrome coronavirus 2"}]}], "doseNumberPositiveInt": 1}], "id": "ca8ba2c6-2383-4465-b456-c1174c21cf31"}'
                                },
                            },
                        },
                    }
                ]
            }
        else:
            return {
                "Records": [
                    {
                        "eventName": "REMOVE",
                        "dynamodb": {
                            "ApproximateCreationDateTime": 1690896000,
                            "Keys": {
                                "PK": {"S": "covid#12345"},
                                "SupplierSystem": {"S": "EMIS"},
                                "Resource": {
                                    "S": '{"resourceType": "Immunization", "contained": [{"resourceType": "Practitioner", "id": "Pract1", "name": [{"family": "O\'Reilly", "given": ["Ellena"]}]}, {"resourceType": "Patient", "id": "Pat1", "identifier": [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9674963871"}], "name": [{"family": "GREIR", "given": ["SABINA"]}], "gender": "female", "birthDate": "2019-01-31", "address": [{"postalCode": "GU14 6TU"}]}], "extension": [{"url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure", "valueCodeableConcept": {"coding": [{"system": "http://snomed.info/sct", "code": "1303503001", "display": "Administration of vaccine product containing only Human orthopneumovirus antigen (procedure)"}]}}], "identifier": [{"system": "https://www.ravs.england.nhs.uk/", "value": "0001_RSV_v5_RUN_2_CDFDPS-742_valid_dose_1"}], "status": "completed", "vaccineCode": {"coding": [{"system": "http://snomed.info/sct", "code": "42605811000001109", "display": "Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd) (product)"}]}, "patient": {"reference": "#Pat1"}, "occurrenceDateTime": "2024-06-10T18:33:25+00:00", "recorded": "2024-06-10T18:33:25+00:00", "primarySource": true, "manufacturer": {"display": "Pfizer"}, "location": {"type": "Location", "identifier": {"value": "J82067", "system": "https://fhir.nhs.uk/Id/ods-organization-code"}}, "lotNumber": "RSVTEST", "expirationDate": "2024-12-31", "site": {"coding": [{"system": "http://snomed.info/sct", "code": "368208006", "display": "Left upper arm structure (body structure)"}]}, "route": {"coding": [{"system": "http://snomed.info/sct", "code": "78421000", "display": "Intramuscular route (qualifier value)"}]}, "doseQuantity": {"value": 0.5, "unit": "Milliliter (qualifier value)", "system": "http://unitsofmeasure.org", "code": "258773002"}, "performer": [{"actor": {"reference": "#Pract1"}}, {"actor": {"type": "Organization", "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "X0X0X"}}}], "reasonCode": [{"coding": [{"code": "Test", "system": "http://snomed.info/sct"}]}], "protocolApplied": [{"targetDisease": [{"coding": [{"system": "http://snomed.info/sct", "code": "840539006", "display": "Disease caused by severe acute respiratory syndrome coronavirus 2"}]}], "doseNumberPositiveInt": 1}], "id": "ca8ba2c6-2383-4465-b456-c1174c21cf31"}'
                                },
                                "PatientSK": {
                                    "S": "COVID19#ca8ba2c6-2383-4465-b456-c1174c21cf31"
                                },
                            },
                        },
                    }
                ]
            }

    @patch("boto3.client")
    def test_send_message_success(self, mock_boto_client):
        # Arrange
        mock_sqs = self.setup_mock_sqs(mock_boto_client)
        record = {"key": "value"}

        # Act
        send_message(record)

        # Assert
        mock_sqs.send_message.assert_called_once_with(
            QueueUrl=os.environ["AWS_SQS_QUEUE_URL"], MessageBody=json.dumps(record)
        )

    @patch("boto3.client")
    @patch("logging.Logger.info")
    def test_send_message_client_error(self, mock_logger_info, mock_boto_client):
        # Arrange
        mock_sqs = MagicMock()
        mock_boto_client.return_value = mock_sqs
        record = {"key": "value"}

        # Simulate ClientError
        error_response = {"Error": {"Code": "500", "Message": "Internal Server Error"}}
        mock_sqs.send_message.side_effect = ClientError(error_response, "SendMessage")

        # Act
        send_message(record)

        # Assert
        mock_logger_info.assert_called_once_with(
            "Error sending record to DLQ: An error occurred (500) when calling the SendMessage operation: Internal Server Error"
        )

    @patch("boto3.resource")
    def test_handler_success_insert(self, mock_boto_resource):
        # Arrange
        self.setup_mock_dynamodb(mock_boto_resource)
        suppilers = ["DPS", "EMIS"]
        for supplier in suppilers:
            event = self.get_event(supplier=supplier)

            # Act
            result = handler(event, self.context)

            # Assert
            self.assertEqual(result["statusCode"], 200)

    @patch("boto3.resource")
    def test_handler_failure(self, mock_boto_resource):
        # Arrange
        self.setup_mock_dynamodb(mock_boto_resource, status_code=500)
        event = self.get_event()

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertEqual(result["statusCode"], 500)

    @patch("boto3.resource")
    def test_handler_success_update(self, mock_boto_resource):
        # Arrange
        self.setup_mock_dynamodb(mock_boto_resource)
        event = self.get_event(event_name="UPDATE", operation="UPDATE")

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertEqual(result["statusCode"], 200)

    @patch("boto3.resource")
    def test_handler_success_remove(self, mock_boto_resource):
        # Arrange
        self.setup_mock_dynamodb(mock_boto_resource)
        event = self.get_event(event_name="REMOVE", operation="DELETE")

        # Act
        result = handler(event, self.context)

        # Assert
        self.assertEqual(result["statusCode"], 200)

    @patch("boto3.resource")
    @patch("boto3.client")
    def test_handler_exception_intrusion_check(
        self, mock_boto_resource, mock_boto_client
    ):
        # Arrange
        self.setup_mock_dynamodb(mock_boto_resource, status_code=500)
        mock_boto_client.return_value = MagicMock()
        event = self.get_event()

        # Act & Assert

        result = handler(event, self.context)
        self.assertEqual(result["statusCode"], 500)

    @patch("boto3.resource")
    @patch("boto3.client")
    def test_handler_exception_intrusion(self, mock_boto_resource, mock_boto_client):
        # Arrange
        self.setUp_mock_resources(mock_boto_resource, mock_boto_client)
        event = self.get_event()
        context = {}

        # Act & Assert
        with self.assertRaises(Exception):
            handler(event, context)

    @patch("boto3.resource")
    @patch("delta.handler")
    def test_handler_exception_intrusion_check_false(
        self, mock_boto_resource, mock_boto_client
    ):
        # Arrange
        self.setUp_mock_resources(mock_boto_resource, mock_boto_client)
        event = self.get_event()
        context = {}

        # Act & Assert
        with self.assertRaises(Exception):
            handler(event, context)

    @patch("delta.firehose_logger.send_log")  # Mock Firehose logger
    @patch("delta.logger.info")  # Mock logging
    def test_dps_record_skipped(self, mock_logger_info, mock_firehose_send_log):
        event = self.get_event(supplier="DPSFULL")
        context = {}

        response = handler(event, context)
        print(f"final response1: {response}")

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"], "Record from DPS skipped for 12345")

        # Check logging and Firehose were called
        mock_logger_info.assert_called_with("Record from DPS skipped for 12345")

    # TODO - amend test once error handling implemented
    @patch("delta.firehose_logger.send_log")
    @patch("delta.logger.info")
    @patch("Converter.Converter")
    @patch("delta.boto3.resource")
    def test_partial_success_with_errors(
        self, mock_dynamodb, mock_converter, mock_logger_info, mock_firehose_send_log
    ):
        mock_converter_instance = MagicMock()
        mock_converter_instance.runConversion.return_value = [{}]
        mock_converter_instance.getErrorRecords.return_value = [
            {"error": "Invalid field"}
        ]
        mock_converter.return_value = mock_converter_instance

        # Mock DynamoDB put_item success
        mock_table = MagicMock()
        mock_dynamodb.return_value.Table.return_value = mock_table
        mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

        event = self.get_event()
        context = {}

        response = handler(event, context)
        print(f"final response: {response}")

        # self.assertEqual(response["statusCode"], 207)
        # self.assertIn("Partial success", response["body"])

        # Check logging and Firehose were called
        # mock_logger_info.assert_called()
        # mock_firehose_send_log.assert_called()
