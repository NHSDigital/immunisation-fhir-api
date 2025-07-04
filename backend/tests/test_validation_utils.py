import unittest
from copy import deepcopy

from base_utils.base_utils import obtain_field_location
from jsonpath_ng.ext import parse
from models.field_locations import FieldLocations
from models.obtain_field_value import ObtainFieldValue
from models.utils.generic_utils import (
    get_current_name_instance,
    obtain_current_name_period,
    patient_and_practitioner_value_and_index,
    obtain_name_field_location,
)

from models.fhir_immunization import ImmunizationValidator
from utils.generic_utils import (
    load_json_data,
)
from utils.values_for_tests import ValidValues, InvalidValues, NameInstances


class TestValidatorUtils(unittest.TestCase):
    """Test immunization pre and post validation utils on the FHIR model"""

    def setUp(self):
        """Set up for each test. This runs before every test"""
        self.json_data = load_json_data(filename="completed_rsv_immunization_event.json")
        self.validator = ImmunizationValidator(add_post_validators=False)
        self.updated_json_data = parse("contained[?(@.resourceType=='Patient')].name").update(
            deepcopy(self.json_data), ValidValues.valid_name_4_instances
        )
        self.updated_PatientandPractitioner_json = parse("contained[?(@.resourceType=='Practitioner')].name").update(
            deepcopy(self.updated_json_data), ValidValues.valid_name_4_instances_practitioner
        )

    def test_get_current_name_instance_multiple_names(self):
        """Tests a multiple name occurrences"""

        test_cases = [
            # Single name instance returns the only name instance and 0th index (given and family name)
            (
                [NameInstances.ValidCurrent.given_and_family_only],
                ValidValues.occurrenceDateTime,
                0,
                NameInstances.ValidCurrent.given_and_family_only,
            ),
            # Multiple name instances returns the "current" name instance index 1
            (
                ValidValues.valid_name_4_instances,
                ValidValues.occurrenceDateTime,
                1,
                ValidValues.valid_name_4_instances[1],
            ),
            # Two name instances with no "use" or period, returns first name instance index 0
            (
                [NameInstances.ValidCurrent.given_and_family_only, NameInstances.ValidCurrent.given_and_family_only],
                ValidValues.occurrenceDateTime,
                0,
                NameInstances.ValidCurrent.given_and_family_only,
            ),
            # Four name instances with periods and no "use", returns "current" name instance index 2
            (
                [
                    NameInstances.ValidCurrent.with_period_start,
                    NameInstances.ValidCurrent.given_and_family_only,
                    NameInstances.ValidCurrent.with_use_official_and_period_start_and_end,
                    NameInstances.ValidCurrent.with_period_start,
                ],
                ValidValues.occurrenceDateTime,
                2,
                NameInstances.ValidCurrent.with_use_official_and_period_start_and_end,
            ),
            # Four invalid name instances, name instance containing family and given returned index 0
            (
                [InvalidValues.name_with_missing_values[0], InvalidValues.name_with_missing_values[1]],
                ValidValues.occurrenceDateTime,
                0,
                InvalidValues.name_with_missing_values[0],
            ),
        ]
        for name_value, occurrence_date, expected_index, expected_name in test_cases:
            result = get_current_name_instance(name_value, occurrence_date)
            self.assertEqual(result, (expected_index, expected_name))

    def test_obtain_current_name_period(self):
        """Test obtaining current name based on period for both Patient and Practitioner."""

        def test_name_period_instances(name_instances):
            """
            Helper function to test name periods for given name instances.
            """
            # Single "current" name instance with vaccine date between period start and end date returns True
            valid_name = name_instances[1]
            current_period = obtain_current_name_period(valid_name["period"], ValidValues.occurrenceDateTime)
            self.assertTrue(current_period)

            # Single name instance with expired period end date before vaccine date returns False
            invalid_name = name_instances[0]
            current_period = obtain_current_name_period(invalid_name["period"], ValidValues.occurrenceDateTime)
            self.assertFalse(current_period)

            # Two name instances, name instance with period start date before vaccinedate is selected
            test_names = [
                {
                    **name_instances[1],
                    "period": {"start": ValidValues.date_before_occurenceDateTime},
                },
                {
                    **name_instances[0],
                    "period": {"start": ValidValues.date_after_occurenceDateatetime},
                },
            ]
            occurrence_date = ValidValues.occurrenceDateTime
            result = get_current_name_instance(test_names, occurrence_date)
            self.assertEqual(
                result,
                (
                    0,
                    {
                        **name_instances[1],
                        "period": {"start": ValidValues.date_before_occurenceDateTime},
                    },
                ),
            )

        test_name_period_instances(ValidValues.valid_name_4_instances)
        test_name_period_instances(ValidValues.valid_name_4_instances_practitioner)

    def test_patient_and_practitioner_value_and_index(self):
        """Test retrieving name value and index from Patient/Practitioner resources."""

        # Json data to input
        valid_json_data = deepcopy(self.json_data)
        updated_valid_json_data = self.updated_PatientandPractitioner_json
        invalid_json_data = deepcopy(self.json_data)

        # Amend test data to move valid data in another index position for test purposes
        updated_practitioner_names = deepcopy(ValidValues.valid_name_4_instances_practitioner)
        updated_patient_names = deepcopy(ValidValues.valid_name_4_instances)

        updated_practitioner_names[0], updated_practitioner_names[2] = (
            updated_practitioner_names[2],
            updated_practitioner_names[0],
        )
        updated_patient_names[1], updated_patient_names[3] = (
            updated_patient_names[3],
            updated_patient_names[1],
        )

        updated_valid_json_data["contained"][0]["name"] = updated_practitioner_names
        updated_valid_json_data["contained"][1]["name"] = updated_patient_names

        # Set up invalid data
        invalid_json_data["contained"][0]["name"] = InvalidValues.name_with_missing_values_practitioner
        invalid_json_data["contained"][1]["name"] = InvalidValues.name_with_missing_values

        test_cases = [
            # Test single patient and practitioner names returns family and given names
            (valid_json_data, "given", "Patient", ["Sarah"], 0),
            (valid_json_data, "family", "Patient", "Taylor", 0),
            (valid_json_data, "given", "Practitioner", ["Florence"], 0),
            (valid_json_data, "family", "Practitioner", "Nightingale", 0),
            # Tests multiple patient and practitioner names returns the "current" name instance
            (updated_valid_json_data, "given", "Patient", ["Sarah"], 3),
            (updated_valid_json_data, "family", "Patient", "Taylor", 3),
            (updated_valid_json_data, "given", "Practitioner", ["Florence"], 1),
            (updated_valid_json_data, "family", "Practitioner", "Night", 1),
            # Testing invalid values returns the only name instance that has family and
            # given from list (3rd index)
            (invalid_json_data, "given", "Patient", "", 3),
            (invalid_json_data, "family", "Patient", "Taylor", 3),
            (invalid_json_data, "given", "Practitioner", "", 3),
            (invalid_json_data, "family", "Practitioner", "Nightingale", 3),
        ]

        for imms, name_value, resource_type, expected_name, expected_index in test_cases:
            name_field, index = patient_and_practitioner_value_and_index(imms, name_value, resource_type)
            self.assertEqual(name_field, expected_name)
            self.assertEqual(index, expected_index)

    def test_obtain_dynamic_field_value(self):
        """Tests obtain_field_value for patient and practitioner name family and given returns
        None if error after patient_and_practitioner_value_and_index is called"""
        valid_json_data = deepcopy(self.json_data)
        valid_json_data["contained"][0]["name"] = NameInstances.Invalid.family_name_only
        valid_json_data["contained"][1]["name"] = NameInstances.Invalid.family_name_only

        # Test single patient and practitioner names returns None on error

        result_patient_given = ObtainFieldValue.patient_name_given(valid_json_data)
        result_patient_family = ObtainFieldValue.patient_name_family(valid_json_data)
        result_practitioner_given = ObtainFieldValue.practitioner_name_given(valid_json_data)
        result_practitioner_family = ObtainFieldValue.practitioner_name_family(valid_json_data)

        test_cases = [
            (result_patient_given),
            (result_patient_family),
            (result_practitioner_given),
            (result_practitioner_family),
        ]

        for result in test_cases:
            self.assertEqual(result, None)

    def test_obtain_name_field_location(self):
        """Tests obtain name field location returns the correct dynamic json location for patient and
        practitioner"""
        valid_json_data = self.updated_PatientandPractitioner_json
        valid_json_data_single = self.json_data

        test_cases = [
            # Four patient and practitioner name instances, name instance containing the "current" name index 1 returned
            (valid_json_data, "given", "Patient", "contained[?(@.resourceType=='Patient')].name[1].given"),
            (valid_json_data, "family", "Patient", "contained[?(@.resourceType=='Patient')].name[1].family"),
            (valid_json_data, "given", "Practitioner", "contained[?(@.resourceType=='Practitioner')].name[1].given"),
            (valid_json_data, "family", "Practitioner", "contained[?(@.resourceType=='Practitioner')].name[1].family"),
            # One name instance, first name instance index 0 returned
            (valid_json_data_single, "given", "Patient", "contained[?(@.resourceType=='Patient')].name[0].given"),
            (valid_json_data_single, "family", "Patient", "contained[?(@.resourceType=='Patient')].name[0].family"),
            (
                valid_json_data_single,
                "given",
                "Practitioner",
                "contained[?(@.resourceType=='Practitioner')].name[0].given",
            ),
            (
                valid_json_data_single,
                "family",
                "Practitioner",
                "contained[?(@.resourceType=='Practitioner')].name[0].family",
            ),
        ]

        for imms, name_value, resource_type, expected_location in test_cases:
            result = obtain_name_field_location(imms, resource_type, name_value)
            self.assertEqual(result, expected_location)


if __name__ == "__main__":
    unittest.main()
