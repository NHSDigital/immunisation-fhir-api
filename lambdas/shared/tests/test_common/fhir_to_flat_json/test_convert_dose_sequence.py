import copy
import json
import unittest

from common.fhir_to_flat_json.converter import Converter
from common.fhir_to_flat_json.mappings import ConversionFieldName
from test_common.fhir_to_flat_json.sample_values import ValuesForTests


class TestDoseSequenceToFlatJson(unittest.TestCase):
    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)

    def _run_test(self, expected_result):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.run_conversion()
        self.assertEqual(flat_json[ConversionFieldName.DOSE_SEQUENCE], expected_result)

    def test_dose_sequence_present_int(self):
        self.request_json_data["protocolApplied"] = [{"doseNumberPositiveInt": 2}]
        self._run_test(expected_result="2")

    def test_dose_sequence_missing(self):
        self.request_json_data["protocolApplied"] = [{}]
        self._run_test(expected_result="")

    def test_dose_sequence_protocol_applied_empty(self):
        self.request_json_data["protocolApplied"] = []
        self._run_test(expected_result="")

    def test_dose_sequence_protocol_applied_absent(self):
        self.request_json_data.pop("protocolApplied", None)
        self._run_test(expected_result="")
