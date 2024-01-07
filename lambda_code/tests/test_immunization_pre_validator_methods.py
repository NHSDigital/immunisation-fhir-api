"""Test immunization pre-validation methods"""

import unittest
from decimal import Decimal

from models.immunization_pre_validators import ImmunizationPreValidators
from .utils import (
    GenericValidatorMethodTests,
    generate_field_location_for_questionnnaire_response,
    generate_field_location_for_extension,
)


class TestPreImmunizationMethodValidators(unittest.TestCase):
    """Test immunization pre-validation methods"""

    def test_patient_identifier_value_valid(self):
        """Test patient_identifier_value"""
        GenericValidatorMethodTests.valid(
            self, ImmunizationPreValidators.patient_identifier_value, ["1234567890"]
        )

    def test_patient_identifier_value_invalid(self):
        """Test patient_identifier_value"""

        # Test is string of length 10
        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.patient_identifier_value,
            field_location="patient -> identifier -> value",
            defined_length=10,
            invalid_length_strings_to_test=["123456789", "12345678901"],
        )

        # Test is a string containing only digits
        invalid_values = ["12345 7890", " 123456789", "123456799 ", "1234  7890"]
        for invalid_value in invalid_values:
            with self.assertRaises(ValueError) as error:
                ImmunizationPreValidators.patient_identifier_value(invalid_value)

            self.assertEqual(
                str(error.exception),
                "patient -> identifier -> value must not contain spaces",
            )

    def test_pre_occurrence_date_time_valid(self):
        """Test ImmunizationPreValidators.occurrence_date_time"""
        valid_items_to_test = [
            "2000-01-01T00:00:00+00:00",  # Time and offset all zeroes
            "1933-12-31T11:11:11+12:45",  # Positive offset (with hours and minutes not 0)
            "1933-12-31T11:11:11-05:00",  # Negative offset
        ]

        GenericValidatorMethodTests.valid(
            self,
            ImmunizationPreValidators.occurrence_date_time,
            valid_items_to_test=valid_items_to_test,
        )

    def test_pre_occurrence_date_time_invalid(self):
        """Test ImmunizationPreValidators.occurrence_date_time"""
        GenericValidatorMethodTests.date_time_invalid(
            self,
            ImmunizationPreValidators.occurrence_date_time,
            field_location="occurrenceDateTime",
        )

    def test_pre_contained_valid(self):
        """Test ImmunizationPreValidators.contained"""
        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.contained,
            valid_items_to_test=[
                [{"resourceType": "QuestionnaireResponse", "status": "completed"}]
            ],
        )

    def test_pre_contained_invalid(self):
        """Test ImmunizationPreValidators.contained"""
        valid_list_element = {
            "resourceType": "QuestionnaireResponse",
            "status": "completed",
        }
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorMethodTests.list_invalid(
            self,
            validator=ImmunizationPreValidators.contained,
            field_location="contained",
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_pre_questionnaire_answer_valid(self):
        """Test ImmunizationPreValidators.questionnaire_answer"""
        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.questionnaire_answer,
            valid_items_to_test=[
                [
                    {"valueCoding": {"code": "B0C4P"}},
                ]
            ],
        )

    def test_pre_questionnaire_answer_invalid(self):
        """Test ImmunizationPreValidators.questionnaire_answer"""
        valid_list_element = {"valueCoding": {"code": "B0C4P"}}
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorMethodTests.list_invalid(
            self,
            validator=ImmunizationPreValidators.questionnaire_answer,
            field_location="contained[0] -> resourceType[QuestionnaireResponse]: "
            + "item[*] -> linkId[*]: answer",
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_pre_questionnaire_site_code_code_valid(self):
        """Test ImmunizationPreValidators.questionnaire_site_code_code"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.questionnaire_site_code_code,
            valid_items_to_test=["B0C4P"],
        )

    def test_pre_questionnaire_site_code_code_invalid(self):
        """Test ImmunizationPreValidators.questionnaire_site_code_code"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.questionnaire_site_code_code,
            field_location=generate_field_location_for_questionnnaire_response(
                "SiteCode", "code"
            ),
        )

    def test_pre_questionnaire_site_name_code_valid(self):
        """Test ImmunizationPreValidators.questionnaire_site_name_code"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.questionnaire_site_name_code,
            valid_items_to_test=["dummy"],
        )

    def test_pre_questionnaire_site_name_code_invalid(self):
        """Test ImmunizationPreValidators.questionnaire_site_name_code"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.questionnaire_site_name_code,
            field_location=generate_field_location_for_questionnnaire_response(
                "SiteName", "code"
            ),
        )

    def test_pre_identifier_valid(self):
        """Test ImmunizationPreValidators.identifier"""

        valid_lists_to_test = [
            [
                {
                    "system": "https://supplierABC/identifiers/vacc",
                    "value": "e045626e-4dc5-4df3-bc35-da25263f901e",
                }
            ]
        ]

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.identifier,
            valid_items_to_test=valid_lists_to_test,
        )

    def test_pre_identifier_invalid(self):
        """Test ImmunizationPreValidators.identifier"""

        valid_list_element = {
            "system": "https://supplierABC/identifiers/vacc",
            "value": "e045626e-4dc5-4df3-bc35-da25263f901e",
        }
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorMethodTests.list_invalid(
            self,
            validator=ImmunizationPreValidators.identifier,
            field_location="identifier",
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_pre_identifier_value_valid(self):
        """Test ImmunizationPreValidators.identifier_value"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.identifier_value,
            valid_items_to_test=[
                "e045626e-4dc5-4df3-bc35-da25263f901e",
                "ACME-vacc123456",
                "ACME-CUSTOMER1-vacc123456",
            ],
        )

    def test_pre_identifier_value_invalid(self):
        """Test ImmunizationPreValidators.identifier_value"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.identifier_value,
            field_location="identifier[0] -> value",
        )

    def test_pre_identifier_system_valid(self):
        """Test ImmunizationPreValidators.identifier_system"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.identifier_system,
            valid_items_to_test=[
                "https://supplierABC/identifiers/vacc",
                "https://supplierABC/ODSCode_NKO41/identifiers/vacc",
            ],
        )

    def test_pre_identifier_system_invalid(self):
        """Test ImmunizationPreValidators.identifier_system"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.identifier_system,
            field_location="identifier[0] -> system",
        )

    def test_pre_status_valid(self):
        """Test ImmunizationPreValidators.status"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.status,
            valid_items_to_test=["completed", "entered-in-error", "not-done"],
        )

    def test_pre_status_invalid(self):
        """Test ImmunizationPreValidators.status"""
        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.status,
            field_location="status",
            predefined_values=("completed", "entered-in-error", "not-done"),
            invalid_strings_to_test=["1", "complete", "enteredinerror"],
        )

    def test_pre_recorded_valid(self):
        """Test ImmunizationPreValidators.recorded"""
        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.recorded,
            valid_items_to_test=["2000-01-01", "1933-12-31"],
        )

    def test_pre_recorded_invalid(self):
        """Test ImmunizationPreValidators.recorded"""

        GenericValidatorMethodTests.date_invalid(
            self,
            validator=ImmunizationPreValidators.recorded,
            field_location="recorded",
        )

    def test_pre_primary_source_valid(self):
        """Test ImmunizationPreValidators.primary_source"""
        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.primary_source,
            valid_items_to_test=[True, False],
        )

    def test_pre_primary_source_invalid(self):
        """Test ImmunizationPreValidators.primary_source"""
        GenericValidatorMethodTests.boolean_invalid(
            self,
            validator=ImmunizationPreValidators.primary_source,
            field_location="primarySource",
        )

    def test_pre_report_origin_text_valid(self):
        """Test ImmunizationPreValidators.report_origin_text"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.report_origin_text,
            valid_items_to_test=[
                "sample",
                "Free text description of organisation recording the event",
            ],
        )

    def test_pre_report_origin_text_invalid(self):
        """Test ImmunizationPreValidators.report_origin_text"""

        invalid_length_strings_to_test = [
            "This is a really long string with more than 100 "
            + "characters to test whether the validator is working well"
        ]
        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.report_origin_text,
            field_location="reportOrigin -> text",
            max_length=100,
            invalid_length_strings_to_test=invalid_length_strings_to_test,
        )

    def test_pre_extension_value_codeable_concept_coding_valid(self):
        """Test ImmunizationPreValidators.extension_value_codeable_concept_coding"""
        valid_items_to_test = [
            [{"system": "http://snomed.info/sct", "code": "ABC123", "display": "test"}]
        ]

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.extension_value_codeable_concept_coding,
            valid_items_to_test=valid_items_to_test,
        )

    def test_pre_extension_value_codeable_concept_coding_invalid(self):
        """Test ImmunizationPreValidators.extension_value_codeable_concept_coding"""
        valid_list_element = {
            "system": "http://snomed.info/sct",
            "code": "ABC123",
            "display": "test",
        }
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorMethodTests.list_invalid(
            self,
            validator=ImmunizationPreValidators.extension_value_codeable_concept_coding,
            field_location="extension[*] -> valueCodeableConcept -> coding",
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_pre_vaccination_procedure_code_valid(self):
        """Test ImmunizationPreValidators.vaccination_procedure_code"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.vaccination_procedure_code,
            valid_items_to_test=["dummy"],
        )

    def test_pre_vaccination_procedure_code_invalid(self):
        """Test ImmunizationPreValidators.vaccination_procedure_code"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.vaccination_procedure_code,
            field_location=generate_field_location_for_extension(
                "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
                "code",
            ),
        )

    def test_pre_vaccination_procedure_display_valid(self):
        """Test ImmunizationPreValidators.vaccination_procedure_display"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.vaccination_procedure_display,
            valid_items_to_test=["dummy"],
        )

    def test_pre_vaccination_procedure_display_invalid(self):
        """Test ImmunizationPreValidators.vaccination_procedure_display"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.vaccination_procedure_display,
            field_location=generate_field_location_for_extension(
                "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
                "display",
            ),
        )

    def test_pre_vaccination_situation_code_valid(self):
        """Test ImmunizationPreValidators.vaccination_situation_code"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.vaccination_situation_code,
            valid_items_to_test=["dummy"],
        )

    def test_pre_vaccination_situation_code_invalid(self):
        """Test ImmunizationPreValidators.vaccination_situation_code"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.vaccination_situation_code,
            field_location=generate_field_location_for_extension(
                "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationSituation",
                "code",
            ),
        )

    def test_pre_vaccination_situation_display_valid(self):
        """Test ImmunizationPreValidators.vaccination_situation_display"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.vaccination_situation_display,
            valid_items_to_test=["dummy"],
        )

    def test_pre_vaccination_situation_display_invalid(self):
        """Test ImmunizationPreValidators.vaccination_situation_display"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.vaccination_situation_display,
            field_location=generate_field_location_for_extension(
                "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationSituation",
                "display",
            ),
        )

    def test_pre_status_reason_coding_valid(self):
        """Test ImmunizationPreValidators.status_reason_coding"""
        valid_items_to_test = [
            [
                {
                    "system": "http://snomed.info/sct",
                    "code": "ABC123",
                    "display": "test",
                }
            ]
        ]

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.status_reason_coding,
            valid_items_to_test=valid_items_to_test,
        )

    def test_pre_status_reason_coding_invalid(self):
        """Test ImmunizationPreValidators.status_reason_coding"""
        valid_list_element = {
            "system": "http://snomed.info/sct",
            "code": "ABC123",
            "display": "test",
        }
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorMethodTests.list_invalid(
            self,
            validator=ImmunizationPreValidators.status_reason_coding,
            field_location="statusReason -> coding",
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_pre_status_reason_coding_code_valid(self):
        """Test ImmunizationPreValidators.status_reason_coding_code"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.status_reason_coding_code,
            valid_items_to_test=["dummy"],
        )

    def test_pre_status_reason_coding_code_invalid(self):
        """Test ImmunizationPreValidators.status_reason_coding_code"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.status_reason_coding_code,
            field_location="statusReason -> coding[0] -> code",
        )

    def test_pre_status_reason_coding_display_valid(self):
        """Test ImmunizationPreValidators.status_reason_coding_display"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.status_reason_coding_display,
            valid_items_to_test=["dummy"],
        )

    def test_pre_status_reason_coding_display_invalid(self):
        """Test ImmunizationPreValidators.status_reason_coding_display"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.status_reason_coding_display,
            field_location="statusReason -> coding[0] -> display",
        )

    def test_pre_protocol_applied_valid(self):
        """Test ImmunizationPreValidators.protocol_applied"""
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

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.protocol_applied,
            valid_items_to_test=valid_items_to_test,
        )

    def test_pre_status_protocol_applied_invalid(self):
        """Test ImmunizationPreValidators.protocol_applied"""
        valid_list_element = {
            "targetDisease": [
                {"coding": [{"code": "ABC123"}]},
                {"coding": [{"code": "DEF456"}]},
            ],
            "doseNumberPositiveInt": 1,
        }
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorMethodTests.list_invalid(
            self,
            validator=ImmunizationPreValidators.protocol_applied,
            field_location="protocolApplied",
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_pre_protocol_applied_dose_number_positive_int_valid(self):
        """Test ImmunizationPreValidators.protocol_applied_dose_number_positive_int"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.protocol_applied_dose_number_positive_int,
            valid_items_to_test=[1, 2, 3, 4, 5, 6, 7, 8, 9],
        )

    def test_pre_protocol_applied_dose_number_positive_int_invalid(self):
        """Test ImmunizationPreValidators.protocol_applied_dose_number_positive_int"""

        # Test invalid data types and non-positive integers
        GenericValidatorMethodTests.positive_integer_invalid(
            self,
            validator=ImmunizationPreValidators.protocol_applied_dose_number_positive_int,
            field_location="protocolApplied[0] -> doseNumberPositiveInt",
        )

        # Test positive integers outside of the range 1 to 9
        invalid_values = [10, 20]

        for invalid_value in invalid_values:
            with self.assertRaises(ValueError) as error:
                ImmunizationPreValidators.protocol_applied_dose_number_positive_int(
                    invalid_value
                )

            self.assertEqual(
                str(error.exception),
                "protocolApplied[0] -> doseNumberPositiveInt must be an integer in "
                + "the range 1 to 9",
            )

    def test_pre_vaccine_code_coding_valid(self):
        """Test ImmunizationPreValidators.vaccine_code_coding"""
        valid_items_to_test = [
            [
                {
                    "system": "http://snomed.info/sct",
                    "code": "ABC123",
                    "display": "test",
                }
            ]
        ]

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.vaccine_code_coding,
            valid_items_to_test=valid_items_to_test,
        )

    def test_pre_status_vaccine_code_coding_invalid(self):
        """Test ImmunizationPreValidators.vaccine_code_coding"""
        valid_list_element = {
            "system": "http://snomed.info/sct",
            "code": "ABC123",
            "display": "test",
        }
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorMethodTests.list_invalid(
            self,
            validator=ImmunizationPreValidators.vaccine_code_coding,
            field_location="vaccineCode -> coding",
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_pre_vaccine_code_coding_code_valid(self):
        """Test ImmunizationPreValidators.vaccine_code_coding_code"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.vaccine_code_coding_code,
            valid_items_to_test=["dummy"],
        )

    def test_pre_vaccine_code_coding_code_invalid(self):
        """Test ImmunizationPreValidators.vaccine_code_coding_code"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.vaccine_code_coding_code,
            field_location="vaccineCode -> coding[0] -> code",
        )

    def test_pre_vaccine_code_coding_display_valid(self):
        """Test ImmunizationPreValidators.vaccine_code_coding_display"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.vaccine_code_coding_display,
            valid_items_to_test=["dummy"],
        )

    def test_pre_vaccine_code_coding_display_invalid(self):
        """Test ImmunizationPreValidators.vaccine_code_coding_display"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.vaccine_code_coding_display,
            field_location="vaccineCode -> coding[0] -> display",
        )

    def test_pre_manufacturer_display_valid(self):
        """Test ImmunizationPreValidators.manufacturer_display"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.manufacturer_display,
            valid_items_to_test=["dummy"],
        )

    def test_pre_manufacturer_display_invalid(self):
        """Test ImmunizationPreValidators.manufacturer_display"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.manufacturer_display,
            field_location="manufacturer -> display",
        )

    def test_pre_lot_number_valid(self):
        """Test ImmunizationPreValidators.lot_number"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.lot_number,
            valid_items_to_test=[
                "sample",
                "0123456789101112",
            ],
        )

    def test_pre_lot_number_invalid(self):
        """Test ImmunizationPreValidators.lot_number"""

        invalid_length_strings_to_test = [
            "This is a really long string with more than 100 "
            + "characters to test whether the validator is working well"
        ]
        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.lot_number,
            field_location="lotNumber",
            max_length=100,
            invalid_length_strings_to_test=invalid_length_strings_to_test,
        )

    def test_pre_expiration_date_valid(self):
        """Test ImmunizationPreValidators.expiration_date"""
        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.expiration_date,
            valid_items_to_test=["2030-01-01", "2003-12-31"],
        )

    def test_pre_expiration_date_invalid(self):
        """Test ImmunizationPreValidators.expiration_date"""

        GenericValidatorMethodTests.date_invalid(
            self,
            validator=ImmunizationPreValidators.expiration_date,
            field_location="expirationDate",
        )

    def test_pre_site_coding_valid(self):
        """Test ImmunizationPreValidators.site_coding"""
        valid_items_to_test = [
            [{"system": "http://snomed.info/sct", "code": "LA", "display": "left arm"}]
        ]

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.site_coding,
            valid_items_to_test=valid_items_to_test,
        )

    def test_pre_status_site_coding_invalid(self):
        """Test ImmunizationPreValidators.site_coding"""
        valid_list_element = {
            "system": "http://snomed.info/sct",
            "code": "LA",
            "display": "left arm",
        }
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorMethodTests.list_invalid(
            self,
            validator=ImmunizationPreValidators.site_coding,
            field_location="site -> coding",
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_pre_site_coding_code_valid(self):
        """Test ImmunizationPreValidators.site_coding_code"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.site_coding_code,
            valid_items_to_test=["dummy"],
        )

    def test_pre_site_coding_code_invalid(self):
        """Test ImmunizationPreValidators.site_coding_code"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.site_coding_code,
            field_location="site -> coding[0] -> code",
        )

    def test_pre_site_coding_display_valid(self):
        """Test ImmunizationPreValidators.site_coding_display"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.site_coding_display,
            valid_items_to_test=["dummy"],
        )

    def test_pre_site_coding_display_invalid(self):
        """Test ImmunizationPreValidators.site_coding_display"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.site_coding_display,
            field_location="site -> coding[0] -> display",
        )

    def test_pre_route_coding_valid(self):
        """Test ImmunizationPreValidators.route_coding"""
        valid_items_to_test = [
            [
                {
                    "system": "http://snomed.info/sct",
                    "code": "IM",
                    "display": "injection, intramuscular",
                }
            ]
        ]

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.route_coding,
            valid_items_to_test=valid_items_to_test,
        )

    def test_pre_route_coding_invalid(self):
        """Test ImmunizationPreValidators.route_coding"""
        valid_list_element = {
            "system": "http://snomed.info/sct",
            "code": "IM",
            "display": "injection, intramuscular",
        }
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorMethodTests.list_invalid(
            self,
            validator=ImmunizationPreValidators.route_coding,
            field_location="route -> coding",
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_pre_route_coding_code_valid(self):
        """Test ImmunizationPreValidators.route_coding_code"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.route_coding_code,
            valid_items_to_test=["dummy"],
        )

    def test_pre_route_coding_code_invalid(self):
        """Test ImmunizationPreValidators.route_coding_code"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.route_coding_code,
            field_location="route -> coding[0] -> code",
        )

    def test_pre_route_coding_display_valid(self):
        """Test ImmunizationPreValidators.route_coding_display"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.route_coding_display,
            valid_items_to_test=["dummy"],
        )

    def test_pre_route_coding_display_invalid(self):
        """Test ImmunizationPreValidators.route_coding_display"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.route_coding_display,
            field_location="route -> coding[0] -> display",
        )

    def test_pre_dose_quantity_value_valid(self):
        """Test ImmunizationPreValidators.dose_quantity_value"""

        valid_items_to_test = [
            1,  # small integer
            100,  # larger integer
            Decimal("1.0"),  # Only 0s after decimal point
            Decimal("0.1"),  # 1 decimal place
            Decimal("100.52"),  # 2 decimal places
            Decimal("32.430"),  # 3 decimal places
            Decimal("1.1234"),  # 4 decimal places
        ]

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.dose_quantity_value,
            valid_items_to_test=valid_items_to_test,
        )

    def test_pre_dose_quantity_value_invalid(self):
        """Test ImmunizationPreValidators.dose_quantity_value"""

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

        for invalid_data_type_to_test in invalid_data_types_to_test:
            with self.assertRaises(TypeError) as error:
                ImmunizationPreValidators.dose_quantity_value(invalid_data_type_to_test)

            self.assertEqual(
                str(error.exception),
                "doseQuantity -> value must be a number",
            )

        # Test Decimals with more than FOUR decimal places
        invalid_items_to_test = [Decimal("1.12345")]

        for invalid_item_to_test in invalid_items_to_test:
            with self.assertRaises(ValueError) as error:
                ImmunizationPreValidators.dose_quantity_value(invalid_item_to_test)

            self.assertEqual(
                str(error.exception),
                "doseQuantity -> value must be a number with a maximum of FOUR decimal places",
            )

    def test_pre_dose_quantity_code_valid(self):
        """Test ImmunizationPreValidators.dose_quantity_code"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.dose_quantity_code,
            valid_items_to_test=["ABC123"],
        )

    def test_pre_dose_quantity_code_invalid(self):
        """Test ImmunizationPreValidators.dose_quantity_code"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.dose_quantity_code,
            field_location="doseQuantity -> code",
        )

    def test_pre_dose_quantity_unit_valid(self):
        """Test ImmunizationPreValidators.dose_quantity_unit"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.dose_quantity_unit,
            valid_items_to_test=["ABC123"],
        )

    def test_pre_dose_quantity_unit_invalid(self):
        """Test ImmunizationPreValidators.dose_quantity_unit"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.dose_quantity_unit,
            field_location="doseQuantity -> unit",
        )

    def test_pre_reason_code_coding_valid(self):
        """Test ImmunizationPreValidators.reason_code_coding"""
        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.reason_code_coding,
            valid_items_to_test=[
                [
                    {"code": "ABC123", "display": "test"},
                ]
            ],
        )

    def test_pre_reason_code_coding_invalid(self):
        """Test ImmunizationPreValidators.reason_code_coding"""
        valid_list_element = {"code": "ABC123", "display": "test"}
        invalid_length_lists_to_test = [[valid_list_element, valid_list_element]]

        GenericValidatorMethodTests.list_invalid(
            self,
            validator=ImmunizationPreValidators.reason_code_coding,
            field_location="reasonCode[*] -> coding",
            predefined_list_length=1,
            invalid_length_lists_to_test=invalid_length_lists_to_test,
        )

    def test_pre_reason_code_coding_code_valid(self):
        """Test ImmunizationPreValidators.reason_code_coding_code"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.reason_code_coding_code,
            valid_items_to_test=["ABC123"],
        )

    def test_pre_reason_code_coding_code_invalid(self):
        """Test ImmunizationPreValidators.reason_code_coding_code"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.reason_code_coding_code,
            field_location="reasonCode[*] -> coding[0] -> code",
        )

    def test_pre_reason_code_coding_display_valid(self):
        """Test ImmunizationPreValidators.reason_code_coding_display"""

        GenericValidatorMethodTests.valid(
            self,
            validator=ImmunizationPreValidators.reason_code_coding_display,
            valid_items_to_test=["ABC123"],
        )

    def test_pre_reason_code_coding_display_invalid(self):
        """Test ImmunizationPreValidators.reason_code_coding_display"""

        GenericValidatorMethodTests.string_invalid(
            self,
            validator=ImmunizationPreValidators.reason_code_coding_display,
            field_location="reasonCode[*] -> coding[0] -> display",
        )
