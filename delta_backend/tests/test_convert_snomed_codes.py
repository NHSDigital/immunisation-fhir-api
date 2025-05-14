import copy
import json
import unittest
from tests.utils_for_converter_tests import ValuesForTests
from Converter import Converter

class TestPersonSNOMEDToFlatJson(unittest.TestCase):

    def setUp(self):
        self.request_json_data = copy.deepcopy(ValuesForTests.json_data)
        
    def _set_snomed_codings(self, target_path: str, codings: list[dict], extension_url: str = None):
        """Helper to insert coding entries into self.request_json_data at the desired FHIR path"""
        if target_path in {"vaccineCode", "site", "route"}:
            self.request_json_data[target_path] = {"coding": codings}
        elif target_path == "reasonCode":
            self.request_json_data["reasonCode"] = [{"coding": codings}]
        elif target_path == "extension":
            self.request_json_data["extension"] = [{
                "url": extension_url or "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
                "valueCodeableConcept": {
                    "coding": codings
                }
            }]

    def _run_snomed_test(self, flat_field_name, expected_snomed_code):
        """Helper function to run the test"""
        self.converter = Converter(json.dumps(self.request_json_data))
        flat_json = self.converter.runConversion(self.request_json_data, False, True)
        self.assertEqual(flat_json.get(flat_field_name), expected_snomed_code)
    
    def test_vaccination_procedure_code(self):
        test_cases = [
            ("no_matching_extension_url", [
                {
                    "url": "https://wrong.url",
                    "valueCodeableConcept": {
                        "coding": [{"code": "123", "system": "http://snomed.info/sct"}]
                    }
                }
            ], "VACCINATION_PROCEDURE_CODE", ""),
            ("empty_coding", [], "VACCINATION_PROCEDURE_CODE", ""),
            ("no_snomed_system", [{"code": "999", "system": "http://example.com/other"}], "VACCINATION_PROCEDURE_CODE", ""),
            ("missing_code_field", [{"system": "http://snomed.info/sct", "display": "No code"}], "VACCINATION_PROCEDURE_CODE", ""),
            ("correct_extension_url_matched", [
                {
                    "url": "https://wrong.url",
                    "valueCodeableConcept": {
                        "coding": [{"code": "1324681000000101", "system": "http://snomed.info/sct"}]
                    }
                },
                {
                    "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
                    "valueCodeableConcept": {
                        "coding": [{"code": "1324681000000102", "system": "http://snomed.info/sct"}]
                    }
                }
            ], "VACCINATION_PROCEDURE_CODE", "1324681000000102"),
            ("single_coding", [{"code": "1324681000000101", "system": "http://snomed.info/sct"}], "VACCINATION_PROCEDURE_CODE", "1324681000000101"),
            ("invalid_then_valid", [
                {"code": "1324681000000101", "system": "http://snomed.info/invalid"},
                {"code": "1324681000000102", "system": "http://snomed.info/sct"}
            ], "VACCINATION_PROCEDURE_CODE", "1324681000000102"),
            ("double_valid", [
                {"code": "1324681000000101", "system": "http://snomed.info/sct"},
                {"code": "1324681000000102", "system": "http://snomed.info/sct"}
            ], "VACCINATION_PROCEDURE_CODE", "1324681000000101"),
        ]

        for name, codings_or_ext, field, expected in test_cases:
            with self.subTest(name=name):
                if name == "no_matching_extension_url" or name == "correct_extension_url_matched":
                    self.request_json_data["extension"] = codings_or_ext
                else:
                    self._set_snomed_codings("extension", codings_or_ext)
                self._run_snomed_test(field, expected)
                
    def test_vaccine_product_code(self):
        test_cases = [
            ("missing_field", None, ""),
            ("no_snomed_system", [{"code": "999999", "system": "http://snomed.info/invalid"}], ""),
            ("empty_coding", [], ""),
            ("single_valid", [{"code": "39114911000001101", "system": "http://snomed.info/sct"}], "39114911000001101"),
            ("double_valid", [
                {"code": "39114911000001101", "system": "http://snomed.info/sct"},
                {"code": "39114911000001102", "system": "http://snomed.info/sct"}
            ], "39114911000001101"),
            ("invalid_then_valid", [
                {"code": "39114911000001101", "system": "http://snomed.info/invalid"},
                {"code": "39114911000001102", "system": "http://snomed.info/sct"}
            ], "39114911000001102"),
        ]

        for name, codings, expected in test_cases:
            with self.subTest(name=name):
                if codings is None:
                    self.request_json_data.pop("vaccineCode", None)
                else:
                    self._set_snomed_codings("vaccineCode", codings)
                self._run_snomed_test("VACCINE_PRODUCT_CODE", expected)
    
    def test_site_of_vaccination_code(self):
        test_cases = [
            ("no_snomed", [{"code": "xyz", "system": "http://example.com/other"}], ""),
            ("empty_coding", [], ""),
            ("missing_field", None, ""),
            ("single_valid", [{"code": "39114911000001101", "system": "http://snomed.info/sct"}], "39114911000001101"),
            ("double_valid", [
                {"code": "39114911000001101", "system": "http://snomed.info/sct"},
                {"code": "39114911000001102", "system": "http://snomed.info/sct"}
            ], "39114911000001101"),
            ("invalid_then_valid", [
                {"code": "39114911000001101", "system": "http://snomed.info/invalid"},
                {"code": "39114911000001102", "system": "http://snomed.info/sct"}
            ], "39114911000001102"),
        ]

        for name, codings, expected in test_cases:
            with self.subTest(name=name):
                if codings is None:
                    self.request_json_data.pop("site", None)
                else:
                    self._set_snomed_codings("site", codings)
                self._run_snomed_test("SITE_OF_VACCINATION_CODE", expected)
                
    def test_route_of_vaccination_code(self):
        test_cases = [
            ("no_snomed", [
                {"code": "xyz", "system": "http://example.org"},
                {"code": "abc", "system": "http://example.net"}
            ], ""),
            ("empty_coding", [], ""),
            ("missing_field", None, ""),
            ("single_valid", [{"code": "39114911000001101", "system": "http://snomed.info/sct"}], "39114911000001101"),
            ("double_valid", [
                {"code": "39114911000001101", "system": "http://snomed.info/sct"},
                {"code": "39114911000001102", "system": "http://snomed.info/sct"}
            ], "39114911000001101"),
            ("invalid_then_valid", [
                {"code": "39114911000001101", "system": "http://snomed.info/invalid"},
                {"code": "39114911000001102", "system": "http://snomed.info/sct"}
            ], "39114911000001102"),
        ]

        for name, codings, expected in test_cases:
            with self.subTest(name=name):
                if codings is None:
                    self.request_json_data.pop("route", None)
                else:
                    self._set_snomed_codings("route", codings)
                self._run_snomed_test("ROUTE_OF_VACCINATION_CODE", expected)

    def test_dose_unit_code(self):
        test_cases = [
            ("valid_snomed", {"code": "258684004", "system": "http://snomed.info/sct"}, "258684004"),
            ("wrong_system", {"code": "258684004", "system": "http://unitsofmeasure.org"}, ""),
            ("missing_system", {"code": "258684004"}, ""),
            ("missing_code", {"system": "http://snomed.info/sct"}, ""),
            ("missing_field", None, "")
        ]

        for name, dose_quantity, expected in test_cases:
            with self.subTest(name=name):
                if dose_quantity is None:
                    self.request_json_data.pop("doseQuantity", None)
                else:
                    self.request_json_data["doseQuantity"] = dose_quantity
                self._run_snomed_test("DOSE_UNIT_CODE", expected)
                
    def test_indication_code(self):
        test_cases = [
            ("single_valid", [{"system": "http://snomed.info/sct", "code": "123456"}], "123456"),
            ("multiple_reasoncodes_first_valid", [
                {"coding": [{"system": "http://snomed.info/sct", "code": "111111"}]},
                {"coding": [{"system": "http://snomed.info/sct", "code": "222222"}]}
            ], "111111"),
            ("skip_invalid_system_use_next_valid", [
                {"coding": [{"system": "http://example.org", "code": "invalid"}]},
                {"coding": [{"system": "http://snomed.info/sct", "code": "999999"}]}
            ], "999999"),
            ("all_invalid_systems", [
                {"coding": [{"system": "http://example.com", "code": "abc"}]},
                {"coding": [{"system": "http://example.org", "code": "def"}]}
            ], ""),
            ("reasoncode_missing", None, ""),
            ("reasoncode_no_coding", [{}], ""),
        ]

        for name, reason_code_value, expected in test_cases:
            with self.subTest(name=name):
                if reason_code_value is None:
                    self.request_json_data.pop("reasonCode", None)
                elif isinstance(reason_code_value[0], dict) and "coding" in reason_code_value[0]:
                    self.request_json_data["reasonCode"] = reason_code_value
                else:
                    self._set_snomed_codings("reasonCode", reason_code_value)
                self._run_snomed_test("INDICATION_CODE", expected)
