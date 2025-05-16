# import unittest
# from unittest.mock import patch, MagicMock
# from delta_converter import Converter
# import exception_messages


# class TestConverter(unittest.TestCase):

#     @patch("delta_converter.FHIRParser")
#     @patch("delta_converter.ConversionLayout")
#     def test_converter_fhir_parser_exception(self,  mock_layout, mock_fhir_parser):
#         mock_layout.return_value.get_conversion_layout.return_value = {"conversions": []}
        
#         # Make FHIRParser.parseFHIRData raise an exception
#         mock_fhir_parser.return_value.parseFHIRData.side_effect = RuntimeError("Mocked FHIR parser failure")

#         converter = Converter({})
#         result = converter.run_conversion()

#         self.assertIsInstance(result, dict)
#         self.assertEqual(result["code"], 0)
#         self.assertIn("Schema getConversions error", result["message"])
#         self.assertEqual(len(converter.getErrorRecords()), 1)
#         self.assertEqual(converter.getErrorRecords()[0], result)
        
#     @patch("delta_converter.FHIRParser")
#     @patch("delta_converter.ConversionLayout")
#     def test_run_conversion_schema_parser_exception(self, mock_getSchemaParser, mock_getFHIRParser):
#         converter = Converter({})
#         mock_getFHIRParser.return_value = MagicMock()
#         mock_getSchemaParser.side_effect = RuntimeError("Mocked Schema parser failure")

#         result = converter.run_conversion()

#         self.assertEqual(result["code"], 0)
#         self.assertIn("Schema Parser Unexpected exception", result["message"])
#         self.assertEqual(len(converter.getErrorRecords()), 1)

#     @patch("delta_converter.FHIRParser")
#     @patch("delta_converter.ConversionLayout")
#     def test_run_conversion_conversion_checker_exception(self, mock_getSchemaParser, mock_getFHIRParser):
#         converter = Converter({})
#         mock_getFHIRParser.return_value = MagicMock()
#         mock_getSchemaParser.return_value = MagicMock()

#         with patch('Converter.ConversionChecker', side_effect=RuntimeError("Mocked Checker failure")):
#             result = converter.run_conversion()
#             self.assertEqual(result["code"], 0)
#             self.assertIn("Expression Checker Unexpected exception", result["message"])

#     @patch("delta_converter.FHIRParser")
#     @patch("delta_converter.ConversionLayout")
#     def test_run_conversion_get_conversions_exception(self, mock_getSchemaParser, mock_getFHIRParser):
#         converter = Converter({})
#         mock_getFHIRParser.return_value = MagicMock()
#         schema_mock = MagicMock()
#         schema_mock.getConversions.side_effect = RuntimeError("Mocked getConversions failure")
#         mock_getSchemaParser.return_value = schema_mock

#         with patch('Converter.ConversionChecker', return_value=MagicMock()):
#             result = converter.run_conversion()
#             self.assertEqual(result["code"], 0)
#             self.assertIn("Expression Getter Unexpected exception", result["message"])


#     @patch("delta_converter.FHIRParser")
#     @patch("delta_converter.ConversionLayout")
#     def test_run_conversion_success(self, mock_checker, mock_schema_parser, mock_fhir_parser):
#         converter = Converter(json_data={"occurrenceDateTime": "2023-01-01T12:00:00"})
#         mock_fhir_parser.return_value.get_key_value.return_value = ["test_value"]
#         mock_schema_parser.return_value.getConversions.return_value = [{
#             "fieldNameFHIR": "someFHIRField",
#             "fieldNameFlat": "someFlatField",
#             "expression": {
#                 "expressionType": "type",
#                 "expressionRule": "rule"
#             }
#         }]
#         checker_instance = MagicMock()
#         checker_instance.convertData.return_value = "converted_value"
#         mock_checker.return_value = checker_instance

#         result = converter.run_conversion()

#         self.assertEqual(len(result), 2)
#         self.assertIn("someFlatField", result)
#         self.assertEqual(result["someFlatField"], "converted_value")

# if __name__ == "__main__":
#     unittest.main()
