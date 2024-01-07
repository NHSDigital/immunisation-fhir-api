"""Test immunization pre validation rules on the model"""
import unittest
import os
import json
from copy import deepcopy
from decimal import Decimal
from pydantic import ValidationError


from models.fhir_immunization import ImmunizationValidator
from .utils import (
    GenericValidatorModelTests,
    generate_field_location_for_questionnnaire_response,
    generate_field_location_for_extension,
    set_in_dict,
)


class TestImmunizationModelPreValidationRules(unittest.TestCase):
    """
    Test immunization pre validation rules on the model

    Notes:-
    TypeErrors and ValueErrors are caught and converted to ValidationErrors by pydantic. When
    this happens, the error message is suffixed with the type of error e.g. type_error or
    value_error. This is why the tests check for the type of error in the error message.

    """

    @classmethod
    def setUpClass(cls):
        """Set up for the tests. This only runs once when the class is instantiated"""
        # Set up the path for the sample data
        cls.data_path = f"{os.path.dirname(os.path.abspath(__file__))}/sample_data"

        # set up the sample immunization event JSON data
        cls.immunization_file_path = f"{cls.data_path}/sample_immunization_event.json"
        with open(cls.immunization_file_path, "r", encoding="utf-8") as f:
            cls.json_data = json.load(f, parse_float=Decimal)

        # set up the untouched sample immunization event JSON data
        cls.untouched_json_data = deepcopy(cls.json_data)

        # set up the validator and add custom root validators
        cls.validator = ImmunizationValidator()
        cls.validator.add_custom_root_validators()

    def setUp(self):
        """Set up for each test. This runs before every test"""
        # Ensure that good data is not inadvertently amended by the tests
        self.assertEqual(self.untouched_json_data, self.json_data)

    def test_model_pre_validate_valid_patient_identifier_value(self):
        """Test pre_validate_patient_identifier_value accepts valid values when in a model"""

        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["patient", "identifier", "value"],
            valid_items_to_test=["1234567890"],
        )

    def test_model_pre_validate_invalid_patient_identifier_value(self):
        """Test pre_validate_patient_identifier_value rejects invalid values when in a model"""

        # Test invalid data types and invalid length strings
        GenericValidatorModelTests.string_invalid(
            self,
            field_location="patient -> identifier -> value",
            keys_to_access_value=["patient", "identifier", "value"],
            defined_length=10,
            invalid_length_strings_to_test=["123456789", "12345678901", ""],
        )

        # Test strings which contain spaces or non-digit characters
        invalid_values = ["12345 7890", " 123456789", "123456789 ", "1234  7890"]

        invalid_json_data = deepcopy(self.json_data)

        for invalid_value in invalid_values:
            invalid_json_data["patient"]["identifier"]["value"] = invalid_value
            with self.assertRaises(ValidationError) as error:
                self.validator.validate(invalid_json_data)

            self.assertTrue(
                "patient -> identifier -> value must not contain spaces (type=value_error)"
                in str(error.exception)
            )

    def test_model_pre_validate_valid_occurrence_date_time(self):
        """Test pre_validate_occurrence_date_time accepts valid values when in a model"""
        valid_items_to_test = [
            "2000-01-01T00:00:00+00:00",  # Time and offset all zeroes
            "1933-12-31T11:11:11+12:45",  # Positive offset (with hours and minutes not 0)
            "1933-12-31T11:11:11-05:00",  # Negative offset
        ]

        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["occurrenceDateTime"],
            valid_items_to_test=valid_items_to_test,
        )

    def test_model_pre_validate_invalid_occurrence_date_time(self):
        """Test pre_validate_occurrence_date_time rejects invalid values when in a model"""
        GenericValidatorModelTests.date_time_invalid(
            self,
            field_location="occurrenceDateTime",
            keys_to_access_value=["occurrenceDateTime"],
            is_occurrence_date_time=True,
        )

    def test_model_pre_validate_valid_contained(self):
        """Test pre_validate_contained accepts valid values when in a model"""
        valid_items_to_test = [
            [{"resourceType": "QuestionnaireResponse", "status": "completed"}]
        ]
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["contained"],
            valid_items_to_test=valid_items_to_test,
        )

    def test_model_pre_validate_invalid_contained(self):
        """Test pre_validate_contained rejects invalid values when in a model"""
        valid_list_element = {
            "resourceType": "QuestionnaireResponse",
            "status": "completed",
        }
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorModelTests.list_invalid(
            self,
            field_location="contained",
            keys_to_access_value=["contained"],
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_model_pre_validate_valid_questionnaire_answers(self):
        """Test pre_validate_questionnaire_answers accepts valid values when in a model"""
        valid_items_to_test = [[{"valueCoding": {"code": "B0C4P"}}]]

        # Check that all of the 12 answer fields in the sample data are accepted when valid
        for i in range(12):
            GenericValidatorModelTests.valid(
                self,
                keys_to_access_value=["contained", 0, "item", i, "answer"],
                valid_items_to_test=valid_items_to_test,
            )

    def test_model_pre_validate_invalid_questionnaire_answers(self):
        """Test pre_validate_quesionnaire_answers rejects invalid values when in a model"""

        valid_list_element = {"valueCoding": {"code": "B0C4P"}}
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        # Check that any of the 12 answer fields in the sample data are rejected when invalid
        for i in range(12):
            GenericValidatorModelTests.list_invalid(
                self,
                field_location="contained[0] -> resourceType[QuestionnaireResponse]: "
                + "item[*] -> linkId[*]: answer",
                keys_to_access_value=["contained", 0, "item", i, "answer"],
                predefined_list_length=1,
                invalid_length_lists_to_test=invalid_length_lists_to_test,
            )

    def test_model_pre_validate_valid_questionnaire_site_code_code(self):
        """Test pre_validate_questionnaire_site_code_code accepts valid values when in a model"""
        keys_to_access_value = [
            "contained",
            0,
            "item",
            0,
            "answer",
            0,
            "valueCoding",
            "code",
        ]

        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=keys_to_access_value,
            valid_items_to_test=["B0C4P"],
        )

    def test_model_pre_validate_invalid_questionnaire_site_code_code(self):
        """Test pre_validate_questionnaire_site_code_code rejects invalid values when in a model"""

        field_location = generate_field_location_for_questionnnaire_response(
            link_id="SiteCode", field_type="code"
        )

        keys_to_access_value = [
            "contained",
            0,
            "item",
            0,
            "answer",
            0,
            "valueCoding",
            "code",
        ]
        GenericValidatorModelTests.string_invalid(
            self,
            field_location=field_location,
            keys_to_access_value=keys_to_access_value,
        )

    def test_model_pre_validate_valid_questionnaire_site_name_code(self):
        """Test pre_validate_questionnaire_site_name_code accepts valid values when in a model"""

        keys_to_access_value = [
            "contained",
            0,
            "item",
            1,
            "answer",
            0,
            "valueCoding",
            "code",
        ]

        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=keys_to_access_value,
            valid_items_to_test=["dummy"],
        )

    def test_model_pre_validate_invalid_questionnaire_site_name_code(self):
        """Test pre_validate_questionnaire_site_code_code rejects invalid values when in a model"""

        field_location = generate_field_location_for_questionnnaire_response(
            link_id="SiteName", field_type="code"
        )

        keys_to_access_value = [
            "contained",
            0,
            "item",
            1,
            "answer",
            0,
            "valueCoding",
            "code",
        ]
        GenericValidatorModelTests.string_invalid(
            self,
            field_location=field_location,
            keys_to_access_value=keys_to_access_value,
        )

    def test_model_pre_validate_valid_identifier(self):
        """Test pre_validate_identifier accepts valid values when in a model"""
        valid_items_to_test = [
            [
                {
                    "system": "https://supplierABC/identifiers/vacc",
                    "value": "ACME-vacc123456",
                }
            ]
        ]

        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["identifier"],
            valid_items_to_test=valid_items_to_test,
        )

    def test_model_pre_validate_invalid_identifier(self):
        """Test pre_validate_identifier rejects invalid values when in a model"""

        valid_list_element = {
            "system": "https://supplierABC/identifiers/vacc",
            "value": "ACME-vacc123456",
        }
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]
        GenericValidatorModelTests.list_invalid(
            self,
            field_location="identifier",
            keys_to_access_value=["identifier"],
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_model_pre_validate_valid_identifier_value(self):
        """Test pre_validate_identifier_value accepts valid values when in a model"""
        valid_items_to_test = [
            "e045626e-4dc5-4df3-bc35-da25263f901e",
            "ACME-vacc123456",
            "ACME-CUSTOMER1-vacc123456",
        ]

        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["identifier", 0, "value"],
            valid_items_to_test=valid_items_to_test,
        )

    def test_model_pre_validate_invalid_identifier_value(self):
        """Test pre_validate_identifier_value rejects invalid values when in a model"""

        GenericValidatorModelTests.string_invalid(
            self,
            field_location="identifier[0] -> value",
            keys_to_access_value=["identifier", 0, "value"],
        )

    def test_model_pre_validate_valid_identifier_system(self):
        """Test pre_validate_identifier_system accepts valid values when in a model"""
        valid_items_to_test = [
            "https://supplierABC/identifiers/vacc",
            "https://supplierABC/ODSCode_NKO41/identifiers/vacc",
        ]

        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["identifier", 0, "system"],
            valid_items_to_test=valid_items_to_test,
        )

    def test_model_pre_validate_invalid_identifier_system(self):
        """Test pre_validate_identifier_system rejects invalid values when in a model"""
        GenericValidatorModelTests.string_invalid(
            self,
            field_location="identifier[0] -> system",
            keys_to_access_value=["identifier", 0, "system"],
        )

    def test_model_pre_validate_valid_status(self):
        """Test pre_validate_status accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["status"],
            valid_items_to_test=["completed", "entered-in-error", "not-done"],
        )

    def test_model_pre_validate_invalid_status(self):
        """Test pre_validate_status rejects invalid values when in a model"""
        GenericValidatorModelTests.string_invalid(
            self,
            field_location="status",
            keys_to_access_value=["status"],
            predefined_values=("completed", "entered-in-error", "not-done"),
            invalid_strings_to_test=["1", "complete", "enteredinerror"],
            is_mandatory_fhir=True,
        )

    def test_model_pre_validate_valid_recorded(self):
        """Test pre_validate_recorded accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["recorded"],
            valid_items_to_test=["2000-01-01", "1933-12-31"],
        )

    def test_model_pre_validate_invalid_recorded(self):
        """Test pre_validate_recorded rejects invalid values when in a model"""
        GenericValidatorModelTests.date_invalid(
            self, field_location="recorded", keys_to_access_value=["recorded"]
        )

    def test_model_pre_validate_valid_primary_source(self):
        """Test pre_validate_primary_source accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["primarySource"],
            valid_items_to_test=[True, False],
        )

    def test_model_pre_validate_invalid_primary_source(self):
        """Test pre_validate_primary_source rejects invalid values when in a model"""
        GenericValidatorModelTests.boolean_invalid(
            self, field_location="primarySource", keys_to_access_value=["primarySource"]
        )

    def test_model_pre_validate_valid_report_origin_text(self):
        """Test pre_validate_report_origin_text accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["reportOrigin", "text"],
            valid_items_to_test=[
                "sample",
                "Free text description of organisation recording the event",
            ],
        )

    def test_model_pre_validate_invalid_report_origin_text(self):
        """Test pre_validate_report_origin_text rejects invalid values when in a model"""
        invalid_length_strings_to_test = [
            "This is a really long string with more than 100 "
            + "characters to test whether the validator is working well"
        ]

        GenericValidatorModelTests.string_invalid(
            self,
            field_location="reportOrigin -> text",
            keys_to_access_value=["reportOrigin", "text"],
            max_length=100,
            invalid_length_strings_to_test=invalid_length_strings_to_test,
        )

    def test_model_pre_validate_valid_extension_value_codeable_concept_codings(self):
        """
        Test pre_validate_extension_value_codeable_concept_codings accepts valid values when in a
        model
        """
        valid_items_to_test = [
            [{"system": "http://snomed.info/sct", "code": "ABC123", "display": "test"}]
        ]

        # Check that both of the relevant coding fields in the sample data are accepted when valid
        for i in range(2):
            GenericValidatorModelTests.valid(
                self,
                keys_to_access_value=["extension", i, "valueCodeableConcept", "coding"],
                valid_items_to_test=valid_items_to_test,
            )

    def test_model_pre_validate_invalid_extension_value_codeable_concept_codings(self):
        """
        Test pre_validate_extension_value_codeable_concept_codings rejects invalid values when
        in a model
        """

        valid_list_element = {
            "system": "http://snomed.info/sct",
            "code": "ABC123",
            "display": "test",
        }
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        # Check that both of the 2 relevant coding fields in the sample data are rejected when
        # invalid
        for i in range(2):
            GenericValidatorModelTests.list_invalid(
                self,
                field_location="extension[*] -> valueCodeableConcept -> coding",
                keys_to_access_value=[
                    "extension",
                    i,
                    "valueCodeableConcept",
                    "coding",
                ],
                predefined_list_length=1,
                invalid_length_lists_to_test=invalid_length_lists_to_test,
            )

    def test_model_pre_validate_valid_vaccination_procedure_code(self):
        """Test pre_validate_vaccination_procedure_code accepts valid values when in a model"""

        keys_to_access_value = [
            "extension",
            0,
            "valueCodeableConcept",
            "coding",
            0,
            "code",
        ]

        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=keys_to_access_value,
            valid_items_to_test=["dummy"],
        )

    def test_model_pre_validate_invalid_vaccination_procedure_code(self):
        """Test pre_validate_vaccination_procedure_code rejects invalid values when in a model"""

        field_location = generate_field_location_for_extension(
            url="https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
            field_type="code",
        )

        keys_to_access_value = [
            "extension",
            0,
            "valueCodeableConcept",
            "coding",
            0,
            "code",
        ]
        GenericValidatorModelTests.string_invalid(
            self,
            field_location=field_location,
            keys_to_access_value=keys_to_access_value,
        )

    def test_model_pre_validate_valid_vaccination_procedure_display(self):
        """Test pre_validate_vaccination_procedure_display accepts valid values when in a model"""

        keys_to_access_value = [
            "extension",
            0,
            "valueCodeableConcept",
            "coding",
            0,
            "display",
        ]

        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=keys_to_access_value,
            valid_items_to_test=["dummy"],
        )

    def test_model_pre_validate_invalid_vaccination_procedure_display(self):
        """Test pre_validate_vaccination_procedure_display rejects invalid values when in a model"""

        field_location = generate_field_location_for_extension(
            url="https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
            field_type="display",
        )

        keys_to_access_value = [
            "extension",
            0,
            "valueCodeableConcept",
            "coding",
            0,
            "display",
        ]
        GenericValidatorModelTests.string_invalid(
            self,
            field_location=field_location,
            keys_to_access_value=keys_to_access_value,
        )

    def test_model_pre_validate_valid_vaccination_situation_code(self):
        """Test pre_validate_vaccination_situation_code accepts valid values when in a model"""

        keys_to_access_value = [
            "extension",
            1,
            "valueCodeableConcept",
            "coding",
            0,
            "code",
        ]

        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=keys_to_access_value,
            valid_items_to_test=["dummy"],
        )

    def test_model_pre_validate_invalid_vaccination_situation_code(self):
        """Test pre_validate_vaccination_situation_code rejects invalid values when in a model"""

        field_location = generate_field_location_for_extension(
            url="https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationSituation",
            field_type="code",
        )

        keys_to_access_value = [
            "extension",
            1,
            "valueCodeableConcept",
            "coding",
            0,
            "code",
        ]
        GenericValidatorModelTests.string_invalid(
            self,
            field_location=field_location,
            keys_to_access_value=keys_to_access_value,
        )

    def test_model_pre_validate_valid_vaccination_situation_display(self):
        """Test pre_validate_vaccination_situation_display accepts valid values when in a model"""

        keys_to_access_value = [
            "extension",
            1,
            "valueCodeableConcept",
            "coding",
            0,
            "display",
        ]

        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=keys_to_access_value,
            valid_items_to_test=["dummy"],
        )

    def test_model_pre_validate_invalid_vaccination_situation_display(self):
        """Test pre_validate_vaccination_situation_display rejects invalid values when in a model"""

        field_location = generate_field_location_for_extension(
            url="https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationSituation",
            field_type="display",
        )

        keys_to_access_value = [
            "extension",
            1,
            "valueCodeableConcept",
            "coding",
            0,
            "display",
        ]
        GenericValidatorModelTests.string_invalid(
            self,
            field_location=field_location,
            keys_to_access_value=keys_to_access_value,
        )

    def test_model_pre_validate_valid_status_reason_coding(self):
        """Test pre_validate_status_reason_coding accepts valid values when in a model"""
        valid_items_to_test = [
            [
                {
                    "system": "http://snomed.info/sct",
                    "code": "ABC123",
                    "display": "test",
                }
            ]
        ]
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["statusReason", "coding"],
            valid_items_to_test=valid_items_to_test,
        )

    def test_model_pre_validate_invalid_status_reason_coding(self):
        """Test pre_validate_status_reason_coding rejects invalid values when in a model"""
        valid_list_element = {
            "system": "http://snomed.info/sct",
            "code": "ABC123",
            "display": "test",
        }
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorModelTests.list_invalid(
            self,
            field_location="statusReason -> coding",
            keys_to_access_value=["statusReason", "coding"],
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_model_pre_validate_valid_status_reason_coding_code(self):
        """Test pre_validate_status_reason_coding_code accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["statusReason", "coding", 0, "code"],
            valid_items_to_test="dummy",
        )

    def test_model_pre_validate_invalid_status_reason_coding_code(self):
        """Test pre_validate_status_reason_coding_code rejects invalid values when in a model"""

        GenericValidatorModelTests.string_invalid(
            self,
            field_location="statusReason -> coding[0] -> code",
            keys_to_access_value=["statusReason", "coding", 0, "code"],
        )

    def test_model_pre_validate_valid_status_reason_coding_display(self):
        """Test pre_validate_status_reason_coding_display accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["statusReason", "coding", 0, "display"],
            valid_items_to_test="dummy",
        )

    def test_model_pre_validate_invalid_status_reason_coding_display(self):
        """Test pre_validate_status_reason_coding_display rejects invalid values when in a model"""

        GenericValidatorModelTests.string_invalid(
            self,
            field_location="statusReason -> coding[0] -> display",
            keys_to_access_value=["statusReason", "coding", 0, "display"],
        )

    def test_model_pre_validate_valid_protocol_applied(self):
        """Test pre_validate_protocol_applied accepts valid values when in a model"""
        valid_items_to_test = [
            [
                {
                    "targetDisease": [
                        {"coding": [{"code": "ABC123"}]},
                        {"coding": [{"code": "DEF456"}]},
                    ],
                    "doseNumberPositiveInt": 1,
                }
            ]
        ]
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["protocolApplied"],
            valid_items_to_test=valid_items_to_test,
        )

    def test_model_pre_validate_invalid_protocol_applied(self):
        """Test pre_validate_protocol_applied rejects invalid values when in a model"""
        valid_list_element = {
            "targetDisease": [
                {"coding": [{"code": "ABC123"}]},
                {"coding": [{"code": "DEF456"}]},
            ],
            "doseNumberPositiveInt": 1,
        }
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorModelTests.list_invalid(
            self,
            field_location="protocolApplied",
            keys_to_access_value=["protocolApplied"],
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_model_pre_validate_valid_protocol_applied_dose_number_positive_int(
        self,
    ):
        """
        Test pre_validate_protocol_applied_dose_number_positive_int accepts valid values when
        in a model
        """
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["protocolApplied", 0, "doseNumberPositiveInt"],
            valid_items_to_test=[1, 2, 3, 4, 5, 6, 7, 8, 9],
        )

    def test_model_pre_validate_invalid_protocol_applied_dose_number_positive_int(
        self,
    ):
        """
        Test pre_validate_protocol_applied_dose_number_positive_int rejects invalid values when in a
        model
        """
        # Test invalid data types and non-positive integers
        GenericValidatorModelTests.positive_integer_invalid(
            self,
            field_location="protocolApplied[0] -> doseNumberPositiveInt",
            keys_to_access_value=["protocolApplied", 0, "doseNumberPositiveInt"],
        )

        # Test positive integers outside of the range 1 to 9
        invalid_values = [10, 20]
        invalid_json_data = deepcopy(self.json_data)

        for invalid_value in invalid_values:
            invalid_json_data["protocolApplied"][0][
                "doseNumberPositiveInt"
            ] = invalid_value
            with self.assertRaises(ValidationError) as error:
                self.validator.validate(invalid_json_data)

            self.assertTrue(
                "protocolApplied[0] -> doseNumberPositiveInt must be an integer in the range 1 to "
                + "9 (type=value_error)"
                in str(error.exception)
            )

    def test_model_pre_validate_valid_vaccine_code_coding(self):
        """Test pre_validate_vaccine_code_coding accepts valid values when in a model"""
        valid_items_to_test = [
            [
                {
                    "system": "http://snomed.info/sct",
                    "code": "ABC123",
                    "display": "test",
                }
            ]
        ]
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["vaccineCode", "coding"],
            valid_items_to_test=valid_items_to_test,
        )

    def test_model_pre_validate_invalid_vaccine_code_coding(self):
        """Test pre_validate_vaccine_code_coding rejects invalid values when in a model"""
        valid_list_element = {
            "system": "http://snomed.info/sct",
            "code": "ABC123",
            "display": "test",
        }
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorModelTests.list_invalid(
            self,
            field_location="vaccineCode -> coding",
            keys_to_access_value=["vaccineCode", "coding"],
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_model_pre_validate_valid_vaccine_code_coding_code(self):
        """Test pre_validate_vaccine_code_coding_code accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["vaccineCode", "coding", 0, "code"],
            valid_items_to_test="dummy",
        )

    def test_model_pre_validate_invalid_vaccine_code_coding_code(self):
        """Test pre_validate_vaccine_code_coding_code rejects invalid values when in a model"""

        GenericValidatorModelTests.string_invalid(
            self,
            field_location="vaccineCode -> coding[0] -> code",
            keys_to_access_value=["vaccineCode", "coding", 0, "code"],
        )

    def test_model_pre_validate_valid_vaccine_code_coding_display(self):
        """Test pre_validate_vaccine_code_coding_display accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["vaccineCode", "coding", 0, "display"],
            valid_items_to_test="dummy",
        )

    def test_model_pre_validate_invalid_vaccine_code_coding_display(self):
        """Test pre_validate_vaccine_code_coding_display rejects invalid values when in a model"""

        GenericValidatorModelTests.string_invalid(
            self,
            field_location="vaccineCode -> coding[0] -> display",
            keys_to_access_value=["vaccineCode", "coding", 0, "display"],
        )

    def test_model_pre_validate_valid_manufacturer_display(self):
        """Test pre_validate_manufacturer_display accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["manufacturer", "display"],
            valid_items_to_test="dummy",
        )

    def test_model_pre_validate_invalid_manufacturer_display(self):
        """Test pre_validate_manufacturer_display rejects invalid values when in a model"""

        GenericValidatorModelTests.string_invalid(
            self,
            field_location="manufacturer -> display",
            keys_to_access_value=["manufacturer", "display"],
        )

    def test_model_pre_validate_valid_lot_number(self):
        """Test pre_validate_lot_number accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["lotNumber"],
            valid_items_to_test=[
                "sample",
                "0123456789101112",
            ],
        )

    def test_model_pre_validate_invalid_lot_number(self):
        """Test pre_validate_lot_number rejects invalid values when in a model"""
        invalid_length_strings_to_test = [
            "This is a really long string with more than 100 "
            + "characters to test whether the validator is working well"
        ]

        GenericValidatorModelTests.string_invalid(
            self,
            field_location="lotNumber",
            keys_to_access_value=["lotNumber"],
            max_length=100,
            invalid_length_strings_to_test=invalid_length_strings_to_test,
        )

    def test_model_pre_validate_valid_expiration_date(self):
        """Test pre_validate_expiration_date accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["expirationDate"],
            valid_items_to_test=["2030-01-01", "2003-12-31"],
        )

    def test_model_pre_validate_invalid_expiration_date(self):
        """Test pre_validate_expiration_date rejects invalid values when in a model"""
        GenericValidatorModelTests.date_invalid(
            self,
            field_location="expirationDate",
            keys_to_access_value=["expirationDate"],
        )

    def test_model_pre_validate_valid_site_coding(self):
        """Test pre_validate_site_coding accepts valid values when in a model"""
        valid_items_to_test = [
            [{"system": "http://snomed.info/sct", "code": "LA", "display": "left arm"}]
        ]
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["site", "coding"],
            valid_items_to_test=valid_items_to_test,
        )

    def test_model_pre_validate_invalid_site_coding(self):
        """Test pre_validate_site_coding rejects invalid values when in a model"""
        valid_list_element = {
            "system": "http://snomed.info/sct",
            "code": "LA",
            "display": "left arm",
        }
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorModelTests.list_invalid(
            self,
            field_location="site -> coding",
            keys_to_access_value=["site", "coding"],
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_model_pre_validate_valid_site_coding_code(self):
        """Test pre_validate_site_coding_code accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["site", "coding", 0, "code"],
            valid_items_to_test="dummy",
        )

    def test_model_pre_validate_invalid_site_coding_code(self):
        """Test pre_validate_site_coding_code rejects invalid values when in a model"""

        GenericValidatorModelTests.string_invalid(
            self,
            field_location="site -> coding[0] -> code",
            keys_to_access_value=["site", "coding", 0, "code"],
        )

    def test_model_pre_validate_valid_site_coding_display(self):
        """Test pre_validate_site_coding_display accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["site", "coding", 0, "display"],
            valid_items_to_test="dummy",
        )

    def test_model_pre_validate_invalid_site_coding_display(self):
        """Test pre_validate_site_coding_display rejects invalid values when in a model"""

        GenericValidatorModelTests.string_invalid(
            self,
            field_location="site -> coding[0] -> display",
            keys_to_access_value=["site", "coding", 0, "display"],
        )

    def test_model_pre_validate_valid_route_coding(self):
        """Test pre_validate_route_coding accepts valid values when in a model"""
        valid_items_to_test = [
            [
                {
                    "system": "http://snomed.info/sct",
                    "code": "IM",
                    "display": "injection, intramuscular",
                }
            ]
        ]
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["route", "coding"],
            valid_items_to_test=valid_items_to_test,
        )

    def test_model_pre_validate_invalid_route_coding(self):
        """Test pre_validate_route_coding rejects invalid values when in a model"""
        valid_list_element = {
            "system": "http://snomed.info/sct",
            "code": "IM",
            "display": "injection, intramuscular",
        }
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorModelTests.list_invalid(
            self,
            field_location="route -> coding",
            keys_to_access_value=["route", "coding"],
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_model_pre_validate_valid_route_coding_code(self):
        """Test pre_validate_route_coding_code accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["route", "coding", 0, "code"],
            valid_items_to_test="dummy",
        )

    def test_model_pre_validate_invalid_route_coding_code(self):
        """Test pre_validate_route_coding_code rejects invalid values when in a model"""

        GenericValidatorModelTests.string_invalid(
            self,
            field_location="route -> coding[0] -> code",
            keys_to_access_value=["route", "coding", 0, "code"],
        )

    def test_model_pre_validate_valid_route_coding_display(self):
        """Test pre_validate_route_coding_display accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["route", "coding", 0, "display"],
            valid_items_to_test="dummy",
        )

    def test_model_pre_validate_invalid_route_coding_display(self):
        """Test pre_validate_route_coding_display rejects invalid values when in a model"""

        GenericValidatorModelTests.string_invalid(
            self,
            field_location="route -> coding[0] -> display",
            keys_to_access_value=["route", "coding", 0, "display"],
        )

    def test_model_pre_validate_valid_dose_quantity_value(self):
        """Test pre_validate_dose_quantity_value accepts valid values when in a model"""
        valid_items_to_test = [
            1,  # small integer
            100,  # larger integer
            Decimal("1.0"),  # Only 0s after decimal point
            Decimal("0.1"),  # 1 decimal place
            Decimal("100.52"),  # 2 decimal places
            Decimal("32.430"),  # 3 decimal places
            Decimal("1.1234"),  # 4 decimal places
        ]

        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["doseQuantity", "value"],
            valid_items_to_test=valid_items_to_test,
        )

    def test_model_pre_validate_invalid_dose_quantity_value(self):
        """Test pre_validate_dose_quantity_value rejects invalid values when in a model"""

        invalid_json_data = deepcopy(self.json_data)

        # Test invalid data types
        invalid_data_types_to_test = [
            None,
            True,
            False,
            "",
            {},
            [],
            (),
            "1.2",
            {"InvalidKey": "InvalidValue"},
            ["Invalid"],
            ("Invalid1", "Invalid2"),
            1.2,  # Validator accepts Decimals, not floats
        ]

        for invalid_data_type in invalid_data_types_to_test:
            set_in_dict(invalid_json_data, ["doseQuantity", "value"], invalid_data_type)
            with self.assertRaises(ValidationError) as error:
                self.validator.validate(invalid_json_data)

            self.assertTrue(
                "doseQuantity -> value must be a number (type=type_error)"
                in str(error.exception)
            )

        # Test Decimals with more than FOUR decimal places
        set_in_dict(invalid_json_data, ["doseQuantity", "value"], Decimal("1.12345"))
        with self.assertRaises(ValidationError) as error:
            self.validator.validate(invalid_json_data)

        self.assertTrue(
            "doseQuantity -> value must be a number with a maximum of FOUR decimal places "
            + "(type=value_error)"
            in str(error.exception)
        )

    def test_model_pre_validate_valid_dose_quantity_code(self):
        """Test pre_validate_dose_quantity_code accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["doseQuantity", "code"],
            valid_items_to_test="ABC123",
        )

    def test_model_pre_validate_invalid_dose_quantity_code(self):
        """Test pre_validate_dose_quantity_code rejects invalid values when in a model"""

        GenericValidatorModelTests.string_invalid(
            self,
            field_location="doseQuantity -> code",
            keys_to_access_value=["doseQuantity", "code"],
        )

    def test_model_pre_validate_valid_dose_quantity_unit(self):
        """Test pre_validate_dose_quantity_unit accepts valid values when in a model"""
        GenericValidatorModelTests.valid(
            self,
            keys_to_access_value=["doseQuantity", "unit"],
            valid_items_to_test="Millilitre",
        )

    def test_model_pre_validate_invalid_dose_quantity_unit(self):
        """Test pre_validate_dose_quantity_unit rejects invalid values when in a model"""

        GenericValidatorModelTests.string_invalid(
            self,
            field_location="doseQuantity -> unit",
            keys_to_access_value=["doseQuantity", "unit"],
        )

    def test_model_pre_validate_valid_reason_code_codings(self):
        """Test pre_validate_reason_code_codings accepts valid values when in a model"""
        valid_items_to_test = [[{"code": "ABC123", "display": "test"}]]

        # Check that both of the reasonCode[*] -> coding fields in the sample data are accepted when
        #  valid
        for i in range(2):
            GenericValidatorModelTests.valid(
                self,
                keys_to_access_value=["reasonCode", i, "coding"],
                valid_items_to_test=valid_items_to_test,
            )

    def test_model_pre_validate_invalid_reason_code_codings(self):
        """Test pre_validate_reason_code_codings rejects invalid values when in a model"""

        valid_list_element = {"code": "ABC123", "display": "test"}
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        # Check that both of the 2 reasonCode[*] -> coding fields in the sample data are rejected
        # when invalid
        for i in range(2):
            GenericValidatorModelTests.list_invalid(
                self,
                field_location="reasonCode[*] -> coding",
                keys_to_access_value=["reasonCode", i, "coding"],
                predefined_list_length=1,
                invalid_length_lists_to_test=invalid_length_lists_to_test,
            )

    def test_model_pre_validate_valid_reason_code_coding_code(self):
        """Test pre_validate_reason_code_coding_code accepts valid values when in a model"""

        # Check that both of the reasonCode[*] -> coding -> code fields in the sample data are
        # accepted when valid
        for i in range(2):
            GenericValidatorModelTests.valid(
                self,
                keys_to_access_value=["reasonCode", i, "coding", 0, "code"],
                valid_items_to_test="ABC123",
            )

    def test_model_pre_validate_invalid_reason_code_coding_code(self):
        """Test pre_validate_reason_code_coding_code rejects invalid values when in a model"""

        # Check that both of the reasonCode[*] -> coding -> code fields in the sample data are
        # rejected when invalid
        for i in range(2):
            GenericValidatorModelTests.string_invalid(
                self,
                field_location="reasonCode[*] -> coding[0] -> code",
                keys_to_access_value=["reasonCode", i, "coding", 0, "code"],
            )

    def test_model_pre_validate_valid_reason_code_coding_display(self):
        """Test pre_validate_reason_code_coding_display accepts valid values when in a model"""

        # Check that both of the reasonCode[*] -> coding -> display fields in the sample data are
        # accepted when valid
        for i in range(2):
            GenericValidatorModelTests.valid(
                self,
                keys_to_access_value=["reasonCode", i, "coding", 0, "display"],
                valid_items_to_test="ABC123",
            )

    def test_model_pre_validate_invalid_reason_code_coding_display(self):
        """Test pre_validate_reason_code_coding_display rejects invalid values when in a model"""

        # Check that both of the reasonCode[*] -> coding -> display fields in the sample data are
        # rejected when invalid
        for i in range(2):
            GenericValidatorModelTests.string_invalid(
                self,
                field_location="reasonCode[*] -> coding[0] -> display",
                keys_to_access_value=["reasonCode", i, "coding", 0, "display"],
            )
