import unittest
from unittest.mock import patch, MagicMock
from delta_converter import Converter
import exception_messages


class TestConverter(unittest.TestCase):

    @patch.object(Converter, '_getFHIRParser')
    def test_runConversion_fhirParserException(self, mock_getFHIRParser):
        converter = Converter({})
        mock_getFHIRParser.side_effect = RuntimeError("Mocked FHIR parser failure")

        result = converter.runConversion()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["code"], 0)
        self.assertIn("FHIR Parser Unexpected exception", result["message"])
        self.assertEqual(len(converter.getErrorRecords()), 1)
        self.assertEqual(converter.getErrorRecords()[0], result)

    @patch.object(Converter, '_getFHIRParser')
    @patch.object(Converter, '_getSchemaParser')
    def test_runConversion_schemaParserException(self, mock_getSchemaParser, mock_getFHIRParser):
        converter = Converter({})
        mock_getFHIRParser.return_value = MagicMock()
        mock_getSchemaParser.side_effect = RuntimeError("Mocked Schema parser failure")

        result = converter.runConversion()

        self.assertEqual(result["code"], 0)
        self.assertIn("Schema Parser Unexpected exception", result["message"])
        self.assertEqual(len(converter.getErrorRecords()), 1)

    @patch.object(Converter, '_getFHIRParser')
    @patch.object(Converter, '_getSchemaParser')
    def test_runConversion_conversionCheckerException(self, mock_getSchemaParser, mock_getFHIRParser):
        converter = Converter({})
        mock_getFHIRParser.return_value = MagicMock()
        mock_getSchemaParser.return_value = MagicMock()

        with patch('Converter.ConversionChecker', side_effect=RuntimeError("Mocked Checker failure")):
            result = converter.runConversion()
            self.assertEqual(result["code"], 0)
            self.assertIn("Expression Checker Unexpected exception", result["message"])

    @patch.object(Converter, '_getFHIRParser')
    @patch.object(Converter, '_getSchemaParser')
    def test_runConversion_getConversionsException(self, mock_getSchemaParser, mock_getFHIRParser):
        converter = Converter({})
        mock_getFHIRParser.return_value = MagicMock()
        schema_mock = MagicMock()
        schema_mock.getConversions.side_effect = RuntimeError("Mocked getConversions failure")
        mock_getSchemaParser.return_value = schema_mock

        with patch('Converter.ConversionChecker', return_value=MagicMock()):
            result = converter.runConversion()
            self.assertEqual(result["code"], 0)
            self.assertIn("Expression Getter Unexpected exception", result["message"])

    @patch.object(Converter, '_getFHIRParser')
    @patch.object(Converter, '_getSchemaParser')
    @patch('Converter.ConversionChecker')
    def test_runConversion_success(self, mock_checker, mock_schema_parser, mock_fhir_parser):
        converter = Converter(json_data={"occurrenceDateTime": "2023-01-01T12:00:00"})
        mock_fhir_parser.return_value.getKeyValue.return_value = ["test_value"]
        mock_schema_parser.return_value.getConversions.return_value = [{
            "fieldNameFHIR": "someFHIRField",
            "fieldNameFlat": "someFlatField",
            "expression": {
                "expressionType": "type",
                "expressionRule": "rule"
            }
        }]
        checker_instance = MagicMock()
        checker_instance.convertData.return_value = "converted_value"
        mock_checker.return_value = checker_instance

        result = converter.runConversion()

        self.assertEqual(len(result), 2)
        self.assertIn("someFlatField", result)
        self.assertEqual(result["someFlatField"], "converted_value")

    @patch('Converter.extract_person_names', return_value=("John", "Doe"))
    @patch('Converter.get_valid_address', return_value="12345")
    @patch('Converter.get_patient', return_value={"name": "John Doe"})
    @patch('Converter.extract_site_code', return_value=("SITE123", "URI456"))
    @patch('Converter.extract_practitioner_names', return_value=("Dr", "Smith"))
    def test_extract_patient_details(self, mock_practitioner, mock_site_code, mock_patient, mock_address, mock_names):
        converter = Converter({})
        json_data = {
            "occurrenceDateTime": "2023-01-01T00:00:00",
            "performer": [],
            "patient": {}
        }

        result = converter.extract_patient_details(json_data, "PERSON_FORENAME")
        self.assertEqual(result, "John")

        result = converter.extract_patient_details(json_data, "PERSON_SURNAME")
        self.assertEqual(result, "Doe")

        result = converter.extract_patient_details(json_data, "PERSON_POSTCODE")
        self.assertEqual(result, "12345")

        result = converter.extract_patient_details(json_data, "SITE_CODE")
        self.assertEqual(result, "SITE123")

        result = converter.extract_patient_details(json_data, "PERFORMING_PROFESSIONAL_SURNAME")
        self.assertEqual(result, "Smith")

        # Pass a malformed datetime to trigger the exception
        json_data = {"occurrenceDateTime": "invalid-date-time"}
   
        with patch.object(Converter, '_log_error', return_value="mocked-error") as mock_log_error:
            converter = Converter({})
            result = converter.extract_patient_details(json_data, "PERSON_SURNAME")

            mock_log_error.assert_called_once()
            error_message = mock_log_error.call_args[0][0]
            error_code = mock_log_error.call_args[1]["code"]

            self.assertIn("DateTime conversion error", error_message)
            self.assertIn("ValueError", error_message)
            self.assertEqual(error_code, exception_messages.UNEXPECTED_EXCEPTION)
            self.assertEqual(result, "mocked-error")

if __name__ == "__main__":
    unittest.main()
