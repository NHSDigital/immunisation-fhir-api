import unittest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
import os

# Set environment variables before importing the module
os.environ['AWS_SQS_QUEUE_URL'] = 'https://sqs.us-east-1.amazonaws.com/123456789012/MyQueue'
os.environ['DELTA_TABLE_NAME'] = 'my_delta_table'
os.environ['SOURCE'] = 'my_source'

from src.delta import send_message, handler  # Import after setting environment variables
import json

class DeltaTestCase(unittest.TestCase):

    @patch('boto3.client')
    def test_send_message_success(self, mock_boto_client):
        # Arrange
        mock_sqs = mock_boto_client.return_value
        record = {"key": "value"}
        
        # Act
        send_message(record)
        
        # Assert
        mock_sqs.send_message.assert_called_once_with(
            QueueUrl=os.environ["AWS_SQS_QUEUE_URL"],
            MessageBody=json.dumps(record)
        )

    @patch('boto3.resource')
    def test_handler_success(self, mock_boto_resource):
        # Arrange
        mock_dynamodb = mock_boto_resource.return_value
        mock_table = mock_dynamodb.Table.return_value
        mock_table.put_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "ApproximateCreationDateTime": 1690896000,
                        "NewImage": {
                            "PK": {"S": "covid#12345"},
                            "PatientSK": {"S": "covid#12345"},
                            "IdentifierPK": {"S": "system#1"},
                            "Operation": {"S": "CREATE"},
                            "Resource": {"S": '{"resourceType": "Immunization", "contained": [{"resourceType": "Practitioner", "id": "Pract1", "name": [{"family": "O\'Reilly", "given": ["Ellena"]}]}, {"resourceType": "Patient", "id": "Pat1", "identifier": [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9674963871"}], "name": [{"family": "GREIR", "given": ["SABINA"]}], "gender": "female", "birthDate": "2019-01-31", "address": [{"postalCode": "GU14 6TU"}]}], "extension": [{"url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure", "valueCodeableConcept": {"coding": [{"system": "http://snomed.info/sct", "code": "1303503001", "display": "Administration of vaccine product containing only Human orthopneumovirus antigen (procedure)"}]}}], "identifier": [{"system": "https://www.ravs.england.nhs.uk/", "value": "0001_RSV_v5_RUN_2_CDFDPS-742_valid_dose_1"}], "status": "completed", "vaccineCode": {"coding": [{"system": "http://snomed.info/sct", "code": "42605811000001109", "display": "Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd) (product)"}]}, "patient": {"reference": "#Pat1"}, "occurrenceDateTime": "2024-06-10T18:33:25+00:00", "recorded": "2024-06-10T18:33:25+00:00", "primarySource": true, "manufacturer": {"display": "Pfizer"}, "location": {"type": "Location", "identifier": {"value": "J82067", "system": "https://fhir.nhs.uk/Id/ods-organization-code"}}, "lotNumber": "RSVTEST", "expirationDate": "2024-12-31", "site": {"coding": [{"system": "http://snomed.info/sct", "code": "368208006", "display": "Left upper arm structure (body structure)"}]}, "route": {"coding": [{"system": "http://snomed.info/sct", "code": "78421000", "display": "Intramuscular route (qualifier value)"}]}, "doseQuantity": {"value": 0.5, "unit": "Milliliter (qualifier value)", "system": "http://unitsofmeasure.org", "code": "258773002"}, "performer": [{"actor": {"reference": "#Pract1"}}, {"actor": {"type": "Organization", "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "X0X0X"}}}], "reasonCode": [{"coding": [{"code": "Test", "system": "http://snomed.info/sct"}]}], "protocolApplied": [{"targetDisease": [{"coding": [{"system": "http://snomed.info/sct", "code": "840539006", "display": "Disease caused by severe acute respiratory syndrome coronavirus 2"}]}], "doseNumberPositiveInt": 1}], "id": "ca8ba2c6-2383-4465-b456-c1174c21cf31"}'},
                             "PatientSK": {"S": "COVID19#ca8ba2c6-2383-4465-b456-c1174c21cf31"},
                        }
                    }
                }
            ]
        }
        context = {}
        
        # Act
        result = handler(event, context)
        
        # Assert
        self.assertEqual(result["statusCode"], 200)
        mock_table.put_item.assert_called_once()

    @patch('boto3.resource')
    def test_handler_success_null_value(self, mock_boto_resource):
        # Arrange
        mock_dynamodb = mock_boto_resource.return_value
        mock_table = mock_dynamodb.Table.return_value
        mock_table.put_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "ApproximateCreationDateTime": 1690896000,
                        "NewImage": {
                            "PK": {"S": "covid#12345"},
                            "PatientSK": {"S": "covid#12345"},
                            "IdentifierPK": {"S": "system#1"},
                            "Operation": {"S": "CREATE"},
                            "Resource": {"S": '{"resourceType": "Immunization", "contained": [{"resourceType": "Practitioner", "id": "Pract1", "name": [{"family": "O\'Reilly", "given": ["Ellena"]}]}, {"resourceType": "Patient", "id": "Pat1", "identifier": [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9674963871"}], "name": [{"family": "GREIR", "given": ["SABINA"]}], "gender": "female", "birthDate": "2019-01-31", "address": [{"postalCode": "GU14 6TU"}]}], "extension": [{"url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure", "valueCodeableConcept": {"coding": [{"system": "http://snomed.info/sct", "code": "1303503001", "display": "Administration of vaccine product containing only Human orthopneumovirus antigen (procedure)"}]}}], "identifier": [{"system": "https://www.ravs.england.nhs.uk/", "value": "0001_RSV_v5_RUN_2_CDFDPS-742_valid_dose_1"}], "status": "completed", "vaccineCode": {"coding": [{"system": "http://snomed.info/sct", "code": "42605811000001109", "display": "Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd) (product)"}]}, "patient": {"reference": "#Pat1"}, "occurrenceDateTime": "2024-06-10T18:33:25+00:00", "recorded": "2024-06-10T18:33:25+00:00", "primarySource": true, "manufacturer": {"display": "Pfizer"}, "location": {"type": "Location", "identifier": {"value": "J82067", "system": "https://fhir.nhs.uk/Id/ods-organization-code"}}, "lotNumber": "RSVTEST", "expirationDate": "2024-12-31", "site": {"coding": [{"system": "http://snomed.info/sct", "code": "368208006", "display": "Left upper arm structure (body structure)"}]}, "route": {"coding": [{"system": "http://snomed.info/sct", "code": "78421000", "display": "Intramuscular route (qualifier value)"}]}, "doseQuantity": {"unit": "Milliliter (qualifier value)", "system": "http://unitsofmeasure.org", "code": "258773002"}, "performer": [{"actor": {"reference": "#Pract1"}}, {"actor": {"type": "Organization", "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "X0X0X"}}}], "reasonCode": [{"coding": [{"code": "Test", "system": "http://snomed.info/sct"}]}], "protocolApplied": [{"targetDisease": [{"coding": [{"system": "http://snomed.info/sct", "code": "840539006", "display": "Disease caused by severe acute respiratory syndrome coronavirus 2"}]}], "doseNumberPositiveInt": 1}], "id": "ca8ba2c6-2383-4465-b456-c1174c21cf31"}'},
                             "PatientSK": {"S": "COVID19#ca8ba2c6-2383-4465-b456-c1174c21cf31"},
                        }
                    }
                }
            ]
        }
        context = {}
        
        # Act
        result = handler(event, context)
        
        # Assert
        self.assertEqual(result["statusCode"], 200)
        mock_table.put_item.assert_called_once()    

    @patch('boto3.resource')
    def test_handler_success_remove(self, mock_boto_resource):
        # Arrange
        mock_dynamodb = mock_boto_resource.return_value
        mock_table = mock_dynamodb.Table.return_value
        mock_table.put_item.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        event = {
            "Records": [
                {
                    "eventName": "REMOVE",
                    "dynamodb": {
                        "ApproximateCreationDateTime": 1690896000,
                        "Keys": {
                            "PK": {"S": "covid#12345"},
                            "PatientSK": {"S": "covid#12345"},
                            
                            "Resource": {"S": '{"resourceType": "Immunization", "contained": [{"resourceType": "Practitioner", "id": "Pract1", "name": [{"family": "O\'Reilly", "given": ["Ellena"]}]}, {"resourceType": "Patient", "id": "Pat1", "identifier": [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9674963871"}], "name": [{"family": "GREIR", "given": ["SABINA"]}], "gender": "female", "birthDate": "2019-01-31", "address": [{"postalCode": "GU14 6TU"}]}], "extension": [{"url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure", "valueCodeableConcept": {"coding": [{"system": "http://snomed.info/sct", "code": "1303503001", "display": "Administration of vaccine product containing only Human orthopneumovirus antigen (procedure)"}]}}], "identifier": [{"system": "https://www.ravs.england.nhs.uk/", "value": "0001_RSV_v5_RUN_2_CDFDPS-742_valid_dose_1"}], "status": "completed", "vaccineCode": {"coding": [{"system": "http://snomed.info/sct", "code": "42605811000001109", "display": "Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd) (product)"}]}, "patient": {"reference": "#Pat1"}, "occurrenceDateTime": "2024-06-10T18:33:25+00:00", "recorded": "2024-06-10T18:33:25+00:00", "primarySource": true, "manufacturer": {"display": "Pfizer"}, "location": {"type": "Location", "identifier": {"value": "J82067", "system": "https://fhir.nhs.uk/Id/ods-organization-code"}}, "lotNumber": "RSVTEST", "expirationDate": "2024-12-31", "site": {"coding": [{"system": "http://snomed.info/sct", "code": "368208006", "display": "Left upper arm structure (body structure)"}]}, "route": {"coding": [{"system": "http://snomed.info/sct", "code": "78421000", "display": "Intramuscular route (qualifier value)"}]}, "doseQuantity": {"value": 0.5, "unit": "Milliliter (qualifier value)", "system": "http://unitsofmeasure.org", "code": "258773002"}, "performer": [{"actor": {"reference": "#Pract1"}}, {"actor": {"type": "Organization", "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "X0X0X"}}}], "reasonCode": [{"coding": [{"code": "Test", "system": "http://snomed.info/sct"}]}], "protocolApplied": [{"targetDisease": [{"coding": [{"system": "http://snomed.info/sct", "code": "840539006", "display": "Disease caused by severe acute respiratory syndrome coronavirus 2"}]}], "doseNumberPositiveInt": 1}], "id": "ca8ba2c6-2383-4465-b456-c1174c21cf31"}'},
                             "PatientSK": {"S": "COVID19#ca8ba2c6-2383-4465-b456-c1174c21cf31"},
                        }
                    }
                }
            ]
        }
        context = {}
        
        # Act
        result = handler(event, context)
        
        # Assert
        self.assertEqual(result["statusCode"], 200)
        mock_table.put_item.assert_called_once()    

    @patch('boto3.resource')
    def test_handler_exception(self, mock_boto_resource):
        # Arrange
        mock_dynamodb = mock_boto_resource.return_value
        mock_table = mock_dynamodb.Table.return_value
        mock_table.put_item.side_effect = Exception("Test Exception")

        event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "ApproximateCreationDateTime": "2021-01-01",
                        "NewImage": {
                            "PK": {"S": "covid#12345"},
                            "PatientSK": {"S": "covid#12345"},
                            "IdentifierPK": {"S": "system#1"},
                            "Operation": {"S": "CREATE"},
                            "Resource": {"S": "{}"},
                        }
                    }
                }
            ]
        }
        context = {}
        
        # Act & Assert
        with self.assertRaises(Exception):
            handler(event, context)         

if __name__ == '__main__':
    unittest.main()
