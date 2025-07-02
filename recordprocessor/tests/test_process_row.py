"""Tests for the process_row module"""

import unittest
from unittest.mock import patch
from copy import deepcopy
from boto3 import client as boto3_client
from moto import mock_s3
from decimal import Decimal


from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    MockFieldDictionaries,
    TargetDiseaseElements
)

from tests.utils_for_recordprocessor_tests.utils_for_recordprocessor_tests import (
    GenericSetUp,
    GenericTearDown,
)
from tests.utils_for_recordprocessor_tests.mock_environment_variables import MOCK_ENVIRONMENT_DICT

with patch("os.environ", MOCK_ENVIRONMENT_DICT):
    from clients import REGION_NAME
    from process_row import process_row

s3_client = boto3_client("s3", region_name=REGION_NAME)
ROW_DETAILS = MockFieldDictionaries.all_fields
Allowed_Operations = {"CREATE", "UPDATE", "DELETE"}


@mock_s3
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestProcessRow(unittest.TestCase):
    """Tests for process_row"""

    def setUp(self) -> None:
        GenericSetUp(s3_client)

    def tearDown(self) -> None:
        GenericTearDown(s3_client)

    def test_process_row_success(self):
        """
        Test that process_row gives the expected output.
        These tests check that the row is valid and matches the expected output.
        """
        # set the expected output from 'process_row' in case of success
        expected_result = {
            "resourceType": "Immunization",
            "status": "completed",
            "protocolApplied": [{
                "targetDisease": [{
                    "coding": [{
                        "system": "http://snomed.info/sct",
                        "code": "55735004",
                        "display": "Respiratory syncytial virus infection (disorder)"
                    }]
                }],
                "doseNumberPositiveInt": 1
            }],
            "reasonCode": [{"coding": [{"system": "http://snomed.info/sct", "code": "1037351000000105"}]}],
            "recorded": "2024-09-04",
            "identifier": [{"value": "RSV_002", "system": "https://www.ravs.england.nhs.uk/"}],
            "patient": {"reference": "#Patient1"},
            "contained": [
                {
                    "id": "Patient1",
                    "resourceType": "Patient",
                    "birthDate": "2008-02-17",
                    "gender": "male",
                    "address": [{"postalCode": "WD25 0DZ"}],
                    "identifier": [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9732928395"}],
                    "name": [{"family": "PEEL", "given": ["PHYLIS"]}],
                },
                {
                    "resourceType": "Practitioner",
                    "id": "Practitioner1",
                    "name": [{"family": "O'Reilly", "given": ["Ellena"]}],
                },
            ],
            "vaccineCode": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "42223111000001107",
                        "display": "Quadrivalent influenza vaccine (split virion, inactivated)",
                    }
                ]
            },
            "manufacturer": {"display": "Sanofi Pasteur"},
            "expirationDate": "2024-09-15",
            "lotNumber": "BN92478105653",
            "extension": [
                {
                    "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
                    "valueCodeableConcept": {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "956951000000104",
                                "display": "RSV vaccination in pregnancy (procedure)",
                            }
                        ]
                    },
                }
            ],
            "occurrenceDateTime": "2024-09-04T18:33:25+00:00",
            "primarySource": True,
            "site": {"coding": [{"system": "http://snomed.info/sct", "code": "368209003", "display": "Right arm"}]},
            "route": {
                "coding": [{"system": "http://snomed.info/sct", "code": "1210999013", "display": "Intradermal use"}]
            },
            "doseQuantity": {
                "value": Decimal("0.3"),
                "unit": "Inhalation - unit of product usage",
                "system": "http://snomed.info/sct",
                "code": "2622896019",
            },
            "performer": [
                {
                    "actor": {
                        "type": "Organization",
                        "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "RVVKC"},
                    }
                },
                {"actor": {"reference": "#Practitioner1"}},
            ],
            "location": {"identifier": {"value": "RJC02", "system": "https://fhir.nhs.uk/Id/ods-organization-code"}},
        }

        self.maxDiff = None

        # call 'process_row' with required details
        imms_fhir_resource = process_row(TargetDiseaseElements.RSV, Allowed_Operations, ROW_DETAILS)
        # validate if the response with expected result
        self.assertDictEqual(imms_fhir_resource["fhir_json"], expected_result)

    def test_process_row_invalid_action_flag(self):
        """
        Test that process_row gives the expected output.
        These tests check that the row is valid and matches the expected output.
        """
        Mock_Row = deepcopy(ROW_DETAILS)
        # setting up the invalid action flag other than 'NEW', 'UPDATE' or 'DELETE'
        Mock_Row["ACTION_FLAG"] = "Invalid"

        # call 'process_row' with required details
        response = process_row(TargetDiseaseElements.RSV, Allowed_Operations, Mock_Row)

        # validate if we got INVALID_ACTION_FLAG in response
        self.assertEqual(response["diagnostics"]["error_type"], "INVALID_ACTION_FLAG")

    def test_process_row_missing_action_flag(self):
        """
        Test that process_row gives the expected output.
        These tests check that the row is valid and matches the expected output.
        """

        Mock_Row = deepcopy(ROW_DETAILS)
        # removing action flag from row
        Mock_Row.pop("ACTION_FLAG")

        # call 'process_row' with required details
        response = process_row(TargetDiseaseElements.RSV, Allowed_Operations, Mock_Row)
        # validate if we got INVALID_ACTION_FLAG in response
        self.assertEqual(response["diagnostics"]["error_type"], "INVALID_ACTION_FLAG")

    def test_process_row_missing_permission(self):
        """
        Test that process_row gives the expected output.
        These tests check that the row is valid and matches the expected output.
        """
        # only create and delete permission. Missing update
        allowed_operation = {"CREATE", "DELETE"}
        # copy row data with Action_Flag = 'Update'
        Mock_Row = deepcopy(ROW_DETAILS)

        # call 'process_row' with required details
        response = process_row(TargetDiseaseElements.RSV, allowed_operation, Mock_Row)
        self.assertEqual(response["diagnostics"]["error_type"], "NO_PERMISSIONS")
        self.assertEqual(response["diagnostics"]["statusCode"], 403)

    def test_process_row_missing_unique_id(self):
        """
        Test that process_row gives the expected output.
        These tests check that the row is valid and matches the expected output.
        """
        # copy row data and remove 'UNIQUE_ID'
        Mock_Row = deepcopy(ROW_DETAILS)
        Mock_Row.pop("UNIQUE_ID")
        # call 'process_row' with required details
        response = process_row(TargetDiseaseElements.RSV, Allowed_Operations, Mock_Row)

        self.assertEqual(response["diagnostics"]["error_type"], "MISSING_UNIQUE_ID")
        self.assertEqual(response["diagnostics"]["statusCode"], 400)

    def test_process_row_missing_unique_id_uri(self):
        """
        Test that process_row gives the expected output.
        These tests check that the row is valid and matches the expected output.
        """
        # copy row data and remove 'UNIQUE_ID_URI'
        Mock_Row = deepcopy(ROW_DETAILS)
        Mock_Row.pop("UNIQUE_ID_URI")
        # call 'process_row' with required details
        response = process_row(TargetDiseaseElements.RSV, Allowed_Operations, Mock_Row)

        self.assertEqual(response["diagnostics"]["error_message"], "UNIQUE_ID or UNIQUE_ID_URI is missing")
        self.assertEqual(response["diagnostics"]["statusCode"], 400)


if __name__ == "__main__":
    unittest.main()
