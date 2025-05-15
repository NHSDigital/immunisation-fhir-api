import copy
import json
import unittest
from tests.utils_for_converter_tests import ValuesForTests
from delta_converter import Converter

class TestPersonSNOMEDTermsToFlatJson(unittest.TestCase):

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
    
    def test_vaccination_procedure_term_text_present(self):
        # Scenario 1: `text` field is present
        self._set_snomed_codings(
            target_path="extension",
            codings=[
                {
                    "code": "dummy",
                    "system": "http://snomed.info/sct"
                }
            ],
            extension_url="https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure"
        )
        self.request_json_data["extension"][0]["valueCodeableConcept"]["text"] = "Procedure term from text"
        self._run_snomed_test("VACCINATION_PROCEDURE_TERM", "Procedure term from text")

    def test_vaccination_procedure_term_from_text(self):
        """Test when valueCodeableConcept.text is present — it takes priority."""
        self.request_json_data["extension"][0]["valueCodeableConcept"]["text"] = "Procedure term from text"
        self._run_snomed_test("VACCINATION_PROCEDURE_TERM", "Procedure term from text")

    def test_vaccination_procedure_term_from_extension_value_string(self):
        """Test fallback to extension.valueString when text is missing."""
        self.request_json_data["extension"][0]["valueCodeableConcept"].pop("text", None)  # Remove text
        self._run_snomed_test("VACCINATION_PROCEDURE_TERM", "Test Value string 123456 COVID19 vaccination")

    def test_vaccination_procedure_term_from_display_fallback(self):
        """Test fallback to display when no extension valueString is present."""
        coding = self.request_json_data["extension"][0]["valueCodeableConcept"]["coding"][0]
        coding.pop("extension", None)  # Remove all extensions
        self.request_json_data["extension"][0]["valueCodeableConcept"].pop("text", None)  # Remove text
        self._run_snomed_test("VACCINATION_PROCEDURE_TERM", 
                              "Administration of first dose of severe acute respiratory syndrome coronavirus 2 vaccine (procedure)")

    def test_vaccination_procedure_term_null_when_nothing_matches(self):
        """Test null return when no text, no extension.valueString, and no display."""
        coding = self.request_json_data["extension"][0]["valueCodeableConcept"]["coding"][0]
        coding.pop("extension", None)
        coding.pop("display", None)
        self.request_json_data["extension"][0]["valueCodeableConcept"].pop("text", None)
        self._run_snomed_test("VACCINATION_PROCEDURE_TERM", "")

    def test_vaccination_procedure_term_skips_non_sct_systems(self):
        """Test that only the first SNOMED SCT system coding is used."""
        # Add a dummy non-SCT coding before the valid one
        self.request_json_data["extension"][0]["valueCodeableConcept"]["text"] = None  # force to fallback path
        codings = self.request_json_data["extension"][0]["valueCodeableConcept"]["coding"]
        codings.insert(0, {
            "system": "http://not-snomed",
            "code": "IGNORE",
            "display": "Ignore this"
        })
        self._run_snomed_test("VACCINATION_PROCEDURE_TERM", "Test Value string 123456 COVID19 vaccination")
        
    def test_vaccine_product_term_from_text(self):
        """Test when vaccineCode.text is present — it takes priority."""
        self.request_json_data["vaccineCode"]["text"] = "Preferred vaccine product text"
        self._run_snomed_test("VACCINE_PRODUCT_TERM", "Preferred vaccine product text")

    def test_vaccine_product_term_from_extension_value_string(self):
        """Test fallback to coding.extension.valueString when text is missing."""
        self.request_json_data["vaccineCode"].pop("text", None)  # Remove text

        # Modify first SNOMED coding
        sct_coding = next(
            c for c in self.request_json_data["vaccineCode"]["coding"]
            if c.get("system") == "http://snomed.info/sct"
        )
        sct_coding["extension"] = [{
            "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-CodingSCTDescDisplay",
            "valueString": "Extension value from vaccine code"
        }]
        self._run_snomed_test("VACCINE_PRODUCT_TERM", "Extension value from vaccine code")

    def test_vaccine_product_term_from_display_fallback(self):
        """Test fallback to display when text and extension.valueString are missing."""
        self.request_json_data["vaccineCode"].pop("text", None)
        sct_coding = next(
            c for c in self.request_json_data["vaccineCode"]["coding"]
            if c.get("system") == "http://snomed.info/sct"
        )
        sct_coding.pop("extension", None)
        sct_coding["display"] = "Display fallback for vaccine"
        self._run_snomed_test("VACCINE_PRODUCT_TERM", "Display fallback for vaccine")

    def test_vaccine_product_term_returns_empty_when_no_data(self):
        """Test returns empty string when no text, no valueString, no display."""
        self.request_json_data["vaccineCode"].pop("text", None)
        sct_coding = next(
            c for c in self.request_json_data["vaccineCode"]["coding"]
            if c.get("system") == "http://snomed.info/sct"
        )
        sct_coding.pop("extension", None)
        sct_coding.pop("display", None)
        self._run_snomed_test("VACCINE_PRODUCT_TERM", "")

    def test_vaccine_product_term_skips_non_sct_codings(self):
        """Test ignores non-SNOMED codings and uses first valid SNOMED coding."""
        self.request_json_data["vaccineCode"].pop("text", None)

        # Insert a non-SNOMED coding before SNOMED ones
        self.request_json_data["vaccineCode"]["coding"].insert(0, {
            "system": "http://not-snomed",
            "code": "IGNORE",
            "display": "Wrong system display"
        })

        sct_coding = next(
            c for c in self.request_json_data["vaccineCode"]["coding"]
            if c.get("system") == "http://snomed.info/sct"
        )
        sct_coding["extension"] = [{
            "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-CodingSCTDescDisplay",
            "valueString": "Valid SNOMED vaccine product"
        }]
        self._run_snomed_test("VACCINE_PRODUCT_TERM", "Valid SNOMED vaccine product")
        
    def test_site_of_vaccination_term_from_text(self):
        """Test when site.text is present — takes highest priority."""
        self.request_json_data["site"]["text"] = "Left arm from text"
        self._run_snomed_test("SITE_OF_VACCINATION_TERM", "Left arm from text")

    def test_site_of_vaccination_term_from_extension_value_string(self):
        """Test fallback to extension.valueString when text is missing."""
        self.request_json_data["site"].pop("text", None)

        sct_coding = next(
            c for c in self.request_json_data["site"]["coding"]
            if c.get("system") == "http://snomed.info/sct"
        )
        sct_coding["extension"] = [{
            "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-CodingSCTDescDisplay",
            "valueString": "Extension site description"
        }]
        self._run_snomed_test("SITE_OF_VACCINATION_TERM", "Extension site description")

    def test_site_of_vaccination_term_from_display(self):
        """Test fallback to display when text and extension are missing."""
        self.request_json_data["site"].pop("text", None)
        sct_coding = next(
            c for c in self.request_json_data["site"]["coding"]
            if c.get("system") == "http://snomed.info/sct"
        )
        sct_coding.pop("extension", None)
        sct_coding["display"] = "Left upper arm (display)"
        self._run_snomed_test("SITE_OF_VACCINATION_TERM", "Left upper arm (display)")

    def test_site_of_vaccination_term_returns_empty_when_no_valid_data(self):
        """Test when no text, no extension, no display."""
        self.request_json_data["site"].pop("text", None)
        sct_coding = next(
            c for c in self.request_json_data["site"]["coding"]
            if c.get("system") == "http://snomed.info/sct"
        )
        sct_coding.pop("extension", None)
        sct_coding.pop("display", None)
        self._run_snomed_test("SITE_OF_VACCINATION_TERM", "")

    def test_site_of_vaccination_term_skips_non_sct_systems(self):
        """Test ignores codings with non-SNOMED systems."""
        self.request_json_data["site"].pop("text", None)

        # Add a non-SNOMED coding first
        self.request_json_data["site"]["coding"].insert(0, {
            "system": "http://not-snomed",
            "code": "XYZ",
            "display": "Invalid display"
        })

        sct_coding = next(
            c for c in self.request_json_data["site"]["coding"]
            if c.get("system") == "http://snomed.info/sct"
        )
        sct_coding["extension"] = [{
            "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-CodingSCTDescDisplay",
            "valueString": "Valid SCT site term"
        }]
        self._run_snomed_test("SITE_OF_VACCINATION_TERM", "Valid SCT site term")

    def test_route_of_vaccination_term_from_text(self):
        """Test when route.text is present — takes highest priority."""
        self.request_json_data["route"]["text"] = "Oral route from text"
        self._run_snomed_test("ROUTE_OF_VACCINATION_TERM", "Oral route from text")

    def test_route_of_vaccination_term_from_extension_value_string(self):
        """Test fallback to extension.valueString when text is missing."""
        self.request_json_data["route"].pop("text", None)

        sct_coding = next(
            c for c in self.request_json_data["route"]["coding"]
            if c.get("system") == "http://snomed.info/sct"
        )
        sct_coding["extension"] = [{
            "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-CodingSCTDescDisplay",
            "valueString": "Intramuscular route from extension"
        }]
        self._run_snomed_test("ROUTE_OF_VACCINATION_TERM", "Intramuscular route from extension")

    def test_route_of_vaccination_term_from_display(self):
        """Test fallback to display when text and extension are missing."""
        self.request_json_data["route"].pop("text", None)
        sct_coding = next(
            c for c in self.request_json_data["route"]["coding"]
            if c.get("system") == "http://snomed.info/sct"
        )
        sct_coding.pop("extension", None)
        sct_coding["display"] = "Intranasal route"
        self._run_snomed_test("ROUTE_OF_VACCINATION_TERM", "Intranasal route")

    def test_route_of_vaccination_term_returns_empty_when_no_valid_data(self):
        """Test returns empty string when no text, extension, or display."""
        self.request_json_data["route"].pop("text", None)
        sct_coding = next(
            c for c in self.request_json_data["route"]["coding"]
            if c.get("system") == "http://snomed.info/sct"
        )
        sct_coding.pop("extension", None)
        sct_coding.pop("display", None)
        self._run_snomed_test("ROUTE_OF_VACCINATION_TERM", "")

    def test_route_of_vaccination_term_skips_non_sct_systems(self):
        """Test that non-SNOMED codings are ignored."""
        self.request_json_data["route"].pop("text", None)

        # Add a non-SNOMED coding first
        self.request_json_data["route"]["coding"].insert(0, {
            "system": "http://not-snomed",
            "code": "999",
            "display": "Invalid non-SCT display"
        })

        sct_coding = next(
            c for c in self.request_json_data["route"]["coding"]
            if c.get("system") == "http://snomed.info/sct"
        )
        sct_coding["extension"] = [{
            "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-CodingSCTDescDisplay",
            "valueString": "Correct route from SCT"
        }]
        self._run_snomed_test("ROUTE_OF_VACCINATION_TERM", "Correct route from SCT")

    def test_dose_unit_term_when_unit_exists(self):
        """Test returns doseQuantity.unit when present."""
        self.request_json_data["doseQuantity"] = {
            "value": 0.5,
            "unit": "milliliter",
            "system": "http://unitsofmeasure.org",
            "code": "ml"
        }
        self._run_snomed_test("DOSE_UNIT_TERM", "milliliter")

    def test_dose_unit_term_returns_empty_when_dose_quantity_absent(self):
        """Test returns empty string when doseQuantity is missing."""
        self.request_json_data.pop("doseQuantity", None)
        self._run_snomed_test("DOSE_UNIT_TERM", "")

    def test_dose_unit_term_returns_empty_when_unit_missing(self):
        """Test returns empty string when doseQuantity.unit is missing."""
        self.request_json_data["doseQuantity"] = {
            "value": 0.5,
            "system": "http://unitsofmeasure.org",
            "code": "ml"
            # unit is missing
        }
        self._run_snomed_test("DOSE_UNIT_TERM", "")
