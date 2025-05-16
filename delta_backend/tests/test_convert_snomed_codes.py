import copy
import json
import unittest
from tests.utils_for_converter_tests import ValuesForTests
from delta_converter import Converter


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
        flat_json = self.converter.run_conversion()
        self.assertEqual(flat_json.get(flat_field_name), expected_snomed_code)
    
    def test_vaccination_procedure_code_no_matching_extension_url_returns_empty(self):
        self.request_json_data["extension"] = [
            {
                "url": "https://wrong.url",
                "valueCodeableConcept": {
                    "coding": [
                        {"code": "123", "system": "http://snomed.info/sct"}
                    ]
                }
            }
        ]
        self._run_snomed_test("VACCINATION_PROCEDURE_CODE", "")
    
    def test_vaccination_procedure_code_empty_coding_returns_empty(self):
        self._set_snomed_codings("extension", [])
        self._run_snomed_test("VACCINATION_PROCEDURE_CODE", "")
    
    def test_vaccination_procedure_code_no_snomed_system_returns_empty(self):
        self._set_snomed_codings("extension", [
            {"code": "999", "system": "http://example.com/other"}
        ])
        self._run_snomed_test("VACCINATION_PROCEDURE_CODE", "")
    
    def test_vaccination_procedure_code_missing_code_field_returns_empty(self):
        self._set_snomed_codings("extension", [
            {"system": "http://snomed.info/sct", "display": "No code"}
        ])
        self._run_snomed_test("VACCINATION_PROCEDURE_CODE", "")
    
    def test_vaccination_procedure_code_correct_extension_url_matched(self):
        self.request_json_data["extension"] = [
            {
                "url": "https://wrong.url",
                "valueCodeableConcept": {
                    "coding": [
                        {"code": "1324681000000101", "system": "http://snomed.info/sct", "display": "..."}
                    ]
                }
            },
            {
                "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
                "valueCodeableConcept": {
                    "coding": [
                        {"code": "1324681000000102", "system": "http://snomed.info/sct", "display": "..."}
                    ]
                }
            }
        ]
        self._run_snomed_test("VACCINATION_PROCEDURE_CODE", "1324681000000102")
    
    def test_vaccination_procedure_code_single_coding_returns_first_code(self):
        self._set_snomed_codings("extension", [
            {"code": "1324681000000101", "system": "http://snomed.info/sct", "display": "..."}
        ])
        self._run_snomed_test("VACCINATION_PROCEDURE_CODE", "1324681000000101")

    def test_vaccination_procedure_code_double_coding_and_incorrect_system_returns_correct_code(self):
        self._set_snomed_codings("extension", [
            {"code": "1324681000000101", "system": "http://snomed.info/invalid", "display": "..."},
            {"code": "1324681000000102", "system": "http://snomed.info/sct", "display": "..."}
        ])
        self._run_snomed_test("VACCINATION_PROCEDURE_CODE", "1324681000000102")

    def test_vaccination_procedure_code_double_coding_returns_first_code(self):
        self._set_snomed_codings("extension", [
            {"code": "1324681000000101", "system": "http://snomed.info/sct", "display": "..."},
            {"code": "1324681000000102", "system": "http://snomed.info/sct", "display": "..."}
        ])
        self._run_snomed_test("VACCINATION_PROCEDURE_CODE", "1324681000000101")

    def test_vaccine_product_code_missing_field_returns_empty(self):
        self.request_json_data.pop("vaccineCode", None)
        self._run_snomed_test("VACCINE_PRODUCT_CODE", "")
    
    def test_vaccine_product_code_no_snomed_returns_empty(self):
        self._set_snomed_codings("vaccineCode", [
            {"code": "999999", "system": "http://snomed.info/invalid", "display": "..."}
        ])
        self._run_snomed_test("VACCINE_PRODUCT_CODE", "")
    
    def test_vaccine_product_code_empty_coding_returns_empty(self):
        self._set_snomed_codings("vaccineCode", [])
        self._run_snomed_test("VACCINE_PRODUCT_CODE", "")
         
    def test_vaccine_product_code_single_coding_returns_first_code(self):
        self._set_snomed_codings("vaccineCode", [
            {"code": "39114911000001101", "system": "http://snomed.info/sct", "display": "..."}
        ])
        self._run_snomed_test("VACCINE_PRODUCT_CODE", "39114911000001101")

    def test_vaccine_product_term_uses_first_snomed_value_string(self):
        self._set_snomed_codings("vaccineCode", [
            {
                "code": "123",
                "system": "http://snomed.info/sct",
                "extension": [
                    {
                        "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-CodingSCTDescDisplay",
                        "valueString": "Preferred display string"
                    }
                ]
            }
        ])
        self._run_snomed_test("VACCINE_PRODUCT_TERM", "Preferred display string")
    
    def test_vaccine_product_code_double_coding_returns_first_code(self):
        self._set_snomed_codings("vaccineCode", [
            {"code": "39114911000001101", "system": "http://snomed.info/sct", "display": "..."},
            {"code": "39114911000001102", "system": "http://snomed.info/sct", "display": "..."}
        ])
        self._run_snomed_test("VACCINE_PRODUCT_CODE", "39114911000001101")

    def test_vaccine_product_code_double_coding_and_incorrect_system_returns_correct_code(self):
        self._set_snomed_codings("vaccineCode", [
            {"code": "39114911000001101", "system": "http://snomed.info/invalid", "display": "..."},
            {"code": "39114911000001102", "system": "http://snomed.info/sct", "display": "..."}
        ])
        self._run_snomed_test("VACCINE_PRODUCT_CODE", "39114911000001102")
    
    def test_site_vaccination_code_no_snomed_returns_empty(self):
        self._set_snomed_codings("site", [
            {"code": "xyz", "system": "http://example.com/other"}
        ])
        self._run_snomed_test("SITE_OF_VACCINATION_CODE", "")  
        
    def test_site_vaccination_code_empty_coding_returns_empty(self):
        self._set_snomed_codings("site", [])
        self._run_snomed_test("SITE_OF_VACCINATION_CODE", "")
        
    def test_site_field_missing_returns_empty(self):
        self.request_json_data.pop("site", None)
        self._run_snomed_test("SITE_OF_VACCINATION_CODE", "")
        
    def test_site_vaccination_code_single_coding_returns_first_code(self):
        self._set_snomed_codings("site", [
            {"code": "39114911000001101", "system": "http://snomed.info/sct", "display": "..."}
        ])
        self._run_snomed_test("SITE_OF_VACCINATION_CODE", "39114911000001101")

    def test_site_vaccination_code_double_coding_returns_first_code(self):
        self._set_snomed_codings("site", [
            {"code": "39114911000001101", "system": "http://snomed.info/sct", "display": "..."},
            {"code": "39114911000001102", "system": "http://snomed.info/sct", "display": "..."}
        ])
        self._run_snomed_test("SITE_OF_VACCINATION_CODE", "39114911000001101")

    def test_site_vaccination_code_double_coding_and_incorrect_system_returns_correct_code(self):
        self._set_snomed_codings("site", [
            {"code": "39114911000001101", "system": "http://snomed.info/invalid", "display": "..."},
            {"code": "39114911000001102", "system": "http://snomed.info/sct", "display": "..."}
        ])
        self._run_snomed_test("SITE_OF_VACCINATION_CODE", "39114911000001102")
    
    def test_route_vaccination_code_no_snomed_returns_empty(self):
        self._set_snomed_codings("route", [
            {"code": "xyz", "system": "http://example.org"},
            {"code": "abc", "system": "http://example.net"}
        ])
        self._run_snomed_test("ROUTE_OF_VACCINATION_CODE", "")
    
    def test_route_vaccination_code_empty_coding_returns_empty(self):
        self._set_snomed_codings("route", [])
        self._run_snomed_test("ROUTE_OF_VACCINATION_CODE", "")
    
    def test_route_field_missing_returns_empty(self):
        self.request_json_data.pop("route", None)
        self._run_snomed_test("ROUTE_OF_VACCINATION_CODE", "")
    
    def test_route_vaccination_code_single_coding_returns_first_code(self):
        self._set_snomed_codings("route", [
            {"code": "39114911000001101", "system": "http://snomed.info/sct", "display": "..."}
        ])
        self._run_snomed_test("ROUTE_OF_VACCINATION_CODE", "39114911000001101")

    def test_route_vaccination_code_double_coding_returns_first_code(self):
        self._set_snomed_codings("route", [
            {"code": "39114911000001101", "system": "http://snomed.info/sct", "display": "..."},
            {"code": "39114911000001102", "system": "http://snomed.info/sct", "display": "..."}
        ])
        self._run_snomed_test("ROUTE_OF_VACCINATION_CODE", "39114911000001101")

    def test_route_vaccination_code_double_coding_and_incorrect_system_returns_correct_code(self):
        self._set_snomed_codings("route", [
            {"code": "39114911000001101", "system": "http://snomed.info/invalid", "display": "..."},
            {"code": "39114911000001102", "system": "http://snomed.info/sct", "display": "..."}
        ])
        self._run_snomed_test("ROUTE_OF_VACCINATION_CODE", "39114911000001102")
        
    def test_dose_unit_code_valid_snomed_returns_code(self):
        self.request_json_data["doseQuantity"] = {
            "code": "258684004",
            "system": "http://snomed.info/sct"
        }
        self._run_snomed_test("DOSE_UNIT_CODE", "258684004")

    def test_dose_unit_code_wrong_system_returns_empty(self):
        self.request_json_data["doseQuantity"] = {
            "code": "258684004",
            "system": "http://unitsofmeasure.org"
        }
        self._run_snomed_test("DOSE_UNIT_CODE", "")

    def test_dose_unit_code_missing_system_returns_empty(self):
        self.request_json_data["doseQuantity"] = {
            "code": "258684004"
        }
        self._run_snomed_test("DOSE_UNIT_CODE", "")

    def test_dose_unit_code_missing_code_returns_empty(self):
        self.request_json_data["doseQuantity"] = {
            "system": "http://snomed.info/sct"
        }
        self._run_snomed_test("DOSE_UNIT_CODE", "")

    def test_dose_unit_code_missing_field_returns_empty(self):
        self.request_json_data.pop("doseQuantity", None)
        self._run_snomed_test("DOSE_UNIT_CODE", "")
        
    def test_indication_code_single_reasoncode_with_valid_snomed(self):
        self._set_snomed_codings("reasonCode", [
            {"system": "http://snomed.info/sct", "code": "123456"}
        ])
        self._run_snomed_test("INDICATION_CODE", "123456")

    def test_indication_code_multiple_reasoncodes_first_with_valid_snomed(self):
        self.request_json_data["reasonCode"] = [
            {"coding": [{"system": "http://snomed.info/sct", "code": "111111"}]},
            {"coding": [{"system": "http://snomed.info/sct", "code": "222222"}]}
        ]
        self._run_snomed_test("INDICATION_CODE", "111111")

    def test_indication_code_skips_invalid_system_and_selects_valid_next(self):
        self.request_json_data["reasonCode"] = [
            {"coding": [{"system": "http://example.org", "code": "invalid"}]},
            {"coding": [{"system": "http://snomed.info/sct", "code": "999999"}]}
        ]
        self._run_snomed_test("INDICATION_CODE", "999999")

    def test_indication_code_all_reasoncodes_invalid_system_returns_empty(self):
        self.request_json_data["reasonCode"] = [
            {"coding": [{"system": "http://example.com", "code": "abc"}]},
            {"coding": [{"system": "http://example.org", "code": "def"}]}
        ]
        self._run_snomed_test("INDICATION_CODE", "")

    def test_indication_code_reasoncode_missing_returns_empty(self):
        self.request_json_data.pop("reasonCode", None)
        self._run_snomed_test("INDICATION_CODE", "")

    def test_indication_code_reasoncode_exists_but_no_coding_returns_empty(self):
        self.request_json_data["reasonCode"] = [{}]
        self._run_snomed_test("INDICATION_CODE", "")
