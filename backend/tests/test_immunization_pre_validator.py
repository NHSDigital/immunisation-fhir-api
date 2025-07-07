"""Test immunization pre validation rules on the model"""

import unittest
from copy import deepcopy
from decimal import Decimal
from unittest.mock import patch

from jsonpath_ng.ext import parse

from clients import redis_client
from models.fhir_immunization import ImmunizationValidator
from models.utils.generic_utils import get_generic_extension_value
from utils.generic_utils import (
    # these have an underscore to avoid pytest collecting them as tests
    test_valid_values_accepted as _test_valid_values_accepted,
    test_invalid_values_rejected as _test_invalid_values_rejected,
    load_json_data,
)
from models.utils.generic_utils import (
    patient_name_given_field_location,
    patient_name_family_field_location,
    practitioner_name_given_field_location,
    practitioner_name_family_field_location,
)
from utils.pre_validation_test_utils import ValidatorModelTests
from utils.values_for_tests import ValidValues, InvalidValues
from models.constants import Constants

class TestImmunizationModelPreValidationRules(unittest.TestCase):
    """Test immunization pre validation rules on the FHIR model using the covid sample data"""


    def setUp(self):
        """Set up for each test. This runs before every test"""
        self.json_data = load_json_data(filename="completed_covid19_immunization_event.json")
        self.validator = ImmunizationValidator(add_post_validators=False)
        self.redis_patcher = patch("models.utils.validation_utils.redis_client")
        self.mock_redis_client = self.redis_patcher.start()
        
        
        
    def tearDown(self):
        patch.stopall()

    def test_collected_errors(self):
        """Test that when passed multiple validation errors, it returns a list of all expected errors."""

        covid_data = deepcopy(self.json_data)

        # add a second identifier instance
        covid_data["identifier"].append({"value": "another_value"})

        # remove coding.code from 'reasonCode'
        covid_data["reasonCode"][0]["coding"][0]["code"] = None

        expected_errors = [
            "Validation errors: identifier must be an array of length 1",
            "reasonCode[0].coding[0].code must be a string",
        ]
        # assert ValueError raised
        with self.assertRaises(ValueError) as cm:
            self.validator.validate(covid_data)

        # extract the error messages from the exception
        actual_errors = str(cm.exception).split("; ")

        # assert length of errors
        assert len(actual_errors) == len(expected_errors)

        # assert the error is in the expected error messages
        for error in actual_errors:
            assert error in expected_errors

    def test_pre_validate_resource_type(self):
        """Test pre_validate_resource_type accepts valid values and rejects invalid values"""
        expected_error_message = (
            "This service only accepts FHIR Immunization Resources (i.e. resourceType must equal 'Immunization')"
        )

        # Case: resourceType == 'Immunization' accepted
        valid_json_data = deepcopy(self.json_data)
        self.assertIsNone(self.validator.validate(valid_json_data))

        # Case: resourceType != 'Immunization' not accepted
        _test_invalid_values_rejected(
            self,
            valid_json_data=valid_json_data,
            field_location="resourceType",
            invalid_value="Patient",
            expected_error_message=expected_error_message,
        )

        # Case: resourceType absent not accepted
        invalid_json_data = deepcopy(self.json_data)
        del invalid_json_data["resourceType"]

        with self.assertRaises(ValueError) as error:
            self.validator.validate(invalid_json_data)

        full_error_message = str(error.exception)
        actual_error_messages = full_error_message.replace("Validation errors: ", "").split("; ")
        self.assertIn(expected_error_message, actual_error_messages)

    def test_pre_validate_top_level_elements(self):
        """Test pre_validate_top_level_elements accepts valid values and rejects invalid values"""
        # ACCEPT: Full resource with id
        valid_json_data = deepcopy(self.json_data)
        valid_json_data["id"] = "an-id"
        self.assertIsNone(self.validator.validate(valid_json_data))

        # REJECT: Immunization with subpotent and reportOrigin elements,
        # Patient with extension element, Practitioner with identifier element
        invalid_json_data = deepcopy(self.json_data)
        invalid_json_data["isSubpotent"] = True
        invalid_json_data["reportOrigin"] = "test"
        invalid_json_data["contained"][1]["extension"] = []
        invalid_json_data["contained"][0]["identifier"] = []
        expected_error_messages = [
            "isSubpotent is not an allowed element of the Immunization resource for this service",
            "reportOrigin is not an allowed element of the Immunization resource for this service",
            "extension is not an allowed element of the Patient resource for this service",
            "identifier is not an allowed element of the Practitioner resource for this service",
        ]

        with self.assertRaises(ValueError) as error:
            self.validator.validate(invalid_json_data)

        full_error_message = str(error.exception)
        actual_error_messages = full_error_message.replace("Validation errors: ", "").split("; ")

        for expected_error_message in expected_error_messages:
            self.assertIn(expected_error_message, actual_error_messages)

    def test_pre_validate_contained_contents(self):
        """Test pre_validate_contained_contents accepts valid values and rejects invalid values"""
        field_location = "contained"
        patient_resource_1 = ValidValues.patient_resource_id_Pat1
        patient_resource_2 = ValidValues.patient_resource_id_Pat2
        practitioner_resource_1 = ValidValues.practitioner_resource_id_Pract1
        practitioner_resource_2 = ValidValues.practitioner_resource_id_Pract2
        non_approved_resource = ValidValues.manufacturer_resource_id_Man1

        valid_lists_to_test = [[patient_resource_1, practitioner_resource_1]]
        ValidatorModelTests.test_list_value(self, "contained", valid_lists_to_test, is_list_of_dicts=True)

        # REJECT: contained absent
        invalid_json_data = deepcopy(self.json_data)
        del invalid_json_data["contained"]

        with self.assertRaises(Exception) as error:
            self.validator.validate(invalid_json_data)

        full_error_message = str(error.exception)
        actual_error_messages = full_error_message.replace("Validation errors: ", "").split("; ")
        self.assertIn("contained is a mandatory field", actual_error_messages)

        # ACCEPT: One patient, no practitioner
        valid_json_data = deepcopy(self.json_data)
        valid_json_data["performer"].pop(0)  # Remove reference to practitioner
        valid_values_to_test = [[patient_resource_1]]
        _test_valid_values_accepted(self, valid_json_data, field_location, valid_values_to_test)

        # ACCEPT: One patient, one practitioner
        valid_values_to_test = [[patient_resource_1, practitioner_resource_1]]
        _test_valid_values_accepted(self, deepcopy(self.json_data), field_location, valid_values_to_test)

        # REJECT: One patient, one practitioner, one non-approved
        invalid_value_to_test = [
            patient_resource_1,
            practitioner_resource_1,
            non_approved_resource,
        ]
        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(self.json_data),
            field_location=field_location,
            invalid_value=invalid_value_to_test,
            expected_error_message="contained must contain only Patient and Practitioner resources",
        )

        # REJECT: One patient, two practitioners
        invalid_value_to_test = [
            patient_resource_1,
            practitioner_resource_1,
            practitioner_resource_2,
        ]
        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(self.json_data),
            field_location=field_location,
            invalid_value=invalid_value_to_test,
            expected_error_message="contained must contain a maximum of one Practitioner resource",
        )

        # REJECT: No patient, one practitioner
        invalid_value_to_test = [practitioner_resource_1]
        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(self.json_data),
            field_location=field_location,
            invalid_value=invalid_value_to_test,
            expected_error_message="contained must contain exactly one Patient resource",
        )

        # REJECT: Two patients, one practitioner
        invalid_value_to_test = [
            patient_resource_1,
            patient_resource_2,
            practitioner_resource_1,
        ]
        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(self.json_data),
            field_location=field_location,
            invalid_value=invalid_value_to_test,
            expected_error_message="contained must contain exactly one Patient resource",
        )

        # Reject: No patient, two practitioners, one non-approved
        invalid_value = [
            practitioner_resource_1,
            practitioner_resource_2,
            non_approved_resource,
        ]

        expected_error_messages = [
            "contained must contain only Patient and Practitioner resources",
            "contained must contain exactly one Patient resource",
            "contained must contain a maximum of one Practitioner resource",
        ]

        # Create invalid json data by amending the value of the relevant field
        invalid_json_data = parse(field_location).update(deepcopy(self.json_data), invalid_value)

        with self.assertRaises(ValueError) as error:
            self.validator.validate(invalid_json_data)

        full_error_message = str(error.exception)
        actual_error_messages = full_error_message.replace("Validation errors: ", "").split("; ")

        for expected_error_message in expected_error_messages:
            self.assertIn(expected_error_message, actual_error_messages)

        # REJECT: Missing patient id
        invalid_json_data = deepcopy(self.json_data)
        del invalid_json_data["contained"][1]["id"]

        with self.assertRaises(ValueError) as error:
            self.validator.validate(invalid_json_data)

        full_error_message = str(error.exception)
        actual_error_messages = full_error_message.replace("Validation errors: ", "").split("; ")

        self.assertIn("The contained Patient resource must have an 'id' field", actual_error_messages)

        # REJECT: Missing practitioner id
        invalid_json_data = deepcopy(self.json_data)
        del invalid_json_data["contained"][0]["id"]

        with self.assertRaises(ValueError) as error:
            self.validator.validate(invalid_json_data)

        full_error_message = str(error.exception)
        actual_error_messages = full_error_message.replace("Validation errors: ", "").split("; ")

        self.assertIn("The contained Practitioner resource must have an 'id' field", actual_error_messages)

        # REJECT: Duplicate id
        invalid_json_data = deepcopy(self.json_data)
        invalid_json_data["contained"][1]["id"] = invalid_json_data["contained"][0]["id"]

        with self.assertRaises(ValueError) as error:
            self.validator.validate(invalid_json_data)

        full_error_message = str(error.exception)
        actual_error_messages = full_error_message.replace("Validation errors: ", "").split("; ")

        self.assertIn("ids must not be duplicated amongst contained resources", actual_error_messages)

    def test_pre_validate_patient_reference(self):
        """Test pre_validate_patient_reference accepts valid values and rejects invalid values"""
        patient_resource_1 = ValidValues.patient_resource_id_Pat1
        practitioner_resource_1 = ValidValues.practitioner_resource_id_Pract1

        valid_contained_with_patient = [patient_resource_1, practitioner_resource_1]

        invalid_contained_with_no_id_in_patient = [
            {"resourceType": "Patient"},
            practitioner_resource_1,
        ]

        valid_patient_pat1 = {"reference": "#Pat1"}
        valid_patient_pat2 = {"reference": "#Pat2"}
        invalid_patient_pat1 = {"reference": "Pat1"}

        # Test case: Pat1 in contained, patient reference is #Pat1 - accept
        ValidatorModelTests.test_valid_combinations_of_contained_and_patient_accepted(
            self, valid_contained_with_patient, valid_patient_pat1
        )

        # Test case: Pat1 in contained, patient reference is Pat1 - reject
        ValidatorModelTests.test_invalid_patient_reference_rejected(
            self,
            valid_contained_with_patient,
            invalid_patient_pat1,
            expected_error_message="patient.reference must be a single reference to a contained Patient resource",
        )

        # Test case: Pat1 in contained, patient reference is #Pat2 - reject
        ValidatorModelTests.test_invalid_patient_reference_rejected(
            self,
            valid_contained_with_patient,
            valid_patient_pat2,
            expected_error_message="The reference '#Pat2' does not match the id of the contained Patient resource",
        )
        # Test case: contained Patient has no id, patient reference is #Pat1 - reject
        ValidatorModelTests.test_invalid_patient_reference_rejected(
            self,
            invalid_contained_with_no_id_in_patient,
            valid_patient_pat1,
            expected_error_message="The contained Patient resource must have an 'id' field",
        )

    def test_pre_validate_practitioner_reference(self):
        """Test pre_validate_practitioner_reference accepts valid values and rejects invalid values"""
        # Set up variables for testing
        field_location = "performer"

        valid_organization = {
            "actor": {
                "type": "Organization",
                "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "B0C4P"},
            }
        }
        valid_practitioner_reference = {"actor": {"reference": "#Pract1"}}
        invalid_practitioner_reference = {"actor": {"reference": "#Pat1"}}

        valid_json_data = deepcopy(self.json_data)
        valid_json_data["contained"] = [
            ValidValues.patient_resource_id_Pat1,
            ValidValues.practitioner_resource_id_Pract1,
        ]

        # ACCEPT: No contained practitioner, no references
        valid_json_data_no_practitioner = deepcopy(self.json_data)
        valid_json_data_no_practitioner["contained"] = [ValidValues.patient_resource_id_Pat1]
        _test_valid_values_accepted(
            self,
            valid_json_data=deepcopy(valid_json_data_no_practitioner),
            field_location=field_location,
            valid_values_to_test=[[valid_organization]],
        )

        # REJECT: No contained practitioner, internal references
        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(valid_json_data_no_practitioner),
            field_location=field_location,
            invalid_value=[valid_organization, invalid_practitioner_reference],
            expected_error_message="performer must not contain internal references when there is no contained "
            + "Practitioner resource",
        )

        # REJECT: Contained practitioner, internal references other than to contained practitioner
        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(valid_json_data),
            field_location=field_location,
            invalid_value=[valid_organization, valid_practitioner_reference, invalid_practitioner_reference],
            expected_error_message="performer must not contain any internal references other than"
            + " to the contained Practitioner resource",
        )

        # ACCEPT: Contained practitioner, one reference to contained practitioner
        _test_valid_values_accepted(
            self,
            valid_json_data=deepcopy(valid_json_data),
            field_location=field_location,
            valid_values_to_test=[[valid_organization, valid_practitioner_reference]],
        )

        # REJECT: Contained practitioner, no reference to contained practitioner
        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(valid_json_data),
            field_location=field_location,
            invalid_value=[valid_organization],
            expected_error_message="contained Practitioner resource id 'Pract1' must be referenced from performer",
        )

        # REJECT: Contained practitioner, 2 references to contained practitioner
        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(valid_json_data),
            field_location=field_location,
            invalid_value=[valid_organization, valid_practitioner_reference, valid_practitioner_reference],
            expected_error_message="contained Practitioner resource id 'Pract1' must only be referenced once"
            + " from performer",
        )

    def test_pre_validate_patient_identifier(self):
        """Test pre_validate_patient_identifier accepts valid values and rejects invalid values"""
        valid_list_element = {
            "system": "https://fhir.nhs.uk/Id/nhs-number",
            "value": "9000000009",
        }
        ValidatorModelTests.test_list_value(
            self,
            field_location="contained[?(@.resourceType=='Patient')].identifier",
            valid_lists_to_test=[[valid_list_element]],
            predefined_list_length=1,
            valid_list_element=valid_list_element,
        )

    def test_pre_validate_patient_identifier_extension(self):
        """Test pre_validate_patient_identifier_extension raises an error if an extension is present"""

        invalid_list_element_with_extension = {
            "system": "https://fhir.nhs.uk/Id/nhs-number",
            "value": "9000000009",
            "extension": [{"url": "example.com", "valueString": "example"}],
        }

        # REJECT identifier if it contains an extension
        _test_invalid_values_rejected(
            test_instance=self,
            valid_json_data=self.json_data,
            field_location="contained[?(@.resourceType=='Patient')].identifier[0]",
            invalid_value=invalid_list_element_with_extension,
            expected_error_message="contained[?(@.resourceType=='Patient')].identifier[0] must not include an extension",
        )

    def test_pre_validate_patient_identifier_value(self):
        """Test pre_validate_patient_identifier_value accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_string_value(
            self,
            field_location="contained[?(@.resourceType=='Patient')].identifier[0].value",
            valid_strings_to_test=["9990548609"],
            defined_length=10,
            invalid_length_strings_to_test=["999054860", "99905486091", ""],
            spaces_allowed=False,
            invalid_strings_with_spaces_to_test=[
                "99905 8609",
                " 990548609",
                "999054860 ",
                "9990  8609",
            ],
        )

    def test_pre_validate_patient_name(self):
        """Test pre_validate_patient_name accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_list_value(
            self,
            field_location="contained[?(@.resourceType=='Patient')].name",
            valid_lists_to_test=[
                [
                    {"family": "Test1", "given": ["TestA"]},
                    {"use": "official", "family": "Test2", "given": ["TestB"]},
                    {"family": "ATest3", "given": ["TestA"], "period": {"start": "2021-02-07T13:28:17+00:00"}},
                ]
            ],
            valid_list_element=[{"family": "Test", "given": ["TestA"]}],
        )

    def test_pre_validate_patient_name_given(self):
        """Test pre_validate_patient_name_given accepts valid values and rejects invalid values"""
        valid_json_data = deepcopy(self.json_data)
        # invalid_json

        ValidatorModelTests.test_list_value(
            self,
            field_location=patient_name_given_field_location(valid_json_data),
            valid_lists_to_test=[["Test"], ["Test test"]],
            valid_list_element="Test",
            is_list_of_strings=True,
        )

    def test_pre_validate_patient_name_family(self):
        """Test pre_validate_patient_name_family accepts valid values and rejects invalid values"""
        valid_json_data = deepcopy(self.json_data)
        ValidatorModelTests.test_string_value(
            self,
            field_location=patient_name_family_field_location(valid_json_data),
            valid_strings_to_test=["test"],
        )

    def test_pre_validate_patient_birth_date(self):
        """Test pre_validate_patient_birth_date accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_date_value(self, field_location="contained[?(@.resourceType=='Patient')].birthDate")

    def test_pre_validate_patient_gender(self):
        """Test pre_validate_patient_gender accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_string_value(
            self,
            field_location="contained[?(@.resourceType=='Patient')].gender",
            valid_strings_to_test=["male", "female", "other", "unknown"],
            predefined_values=["male", "female", "other", "unknown"],
            invalid_strings_to_test=InvalidValues.for_genders,
        )

    def test_pre_validate_patient_address(self):
        """Test pre_validate_patient_address accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_list_value(
            self,
            field_location="contained[?(@.resourceType=='Patient')].address",
            valid_lists_to_test=[[{"postalCode": "AA1 1AA"}, {"postalCode": "75007"}, {"postalCode": "AA11AA"}]],
            valid_list_element={"family": "Test"},
        )

    def test_pre_validate_patient_address_postal_code(self):
        """Test pre_validate_patient_address_postal_code accepts valid values and rejects invalid values"""
        values = {
            "contained": [
                {
                    "resourceType": "Patient",
                    "address": [
                        {"city": ""},
                        {"postalCode": ""},
                        {"postalCode": "LS1 MH3"}
                    ]
                }
            ]
        }
        result = self.validator.run_postalCode_validator(values)
        self.assertIsNone(result)

    def test_pre_validate_occurrence_date_time(self):
        """Test pre_validate_occurrence_date_time accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_date_time_value(
            self, field_location="occurrenceDateTime", is_occurrence_date_time=True
        )

    def test_pre_validate_performer(self):
        """Test pre_validate_performer accepts valid values and rejects invalid values"""
        # Test that valid data is accepted
        _test_valid_values_accepted(self, deepcopy(self.json_data), "performer", [ValidValues.performer])

        # Test lists with duplicate values
        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(self.json_data),
            field_location="performer",
            invalid_value=InvalidValues.performer_with_two_organizations,
            expected_error_message=(
                "There must be exactly one performer.actor[?@.type=='Organization'] with type 'Organization'"
            ),
        )

        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(self.json_data),
            field_location="performer",
            invalid_value=InvalidValues.performer_with_no_organizations,
            expected_error_message=(
                "There must be exactly one performer.actor[?@.type=='Organization'] with type 'Organization'"
            ),
        )

    def test_pre_validate_organization_identifier_value(self):
        """Test pre_validate_organization_identifier_value accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_string_value(
            self,
            field_location="performer[?(@.actor.type=='Organization')].actor.identifier.value",
            valid_strings_to_test=["B0C4P"],
        )

    def test_pre_validate_identifier(self):
        """Test pre_validate_identifier accepts valid values and rejects invalid values"""
        # Test absent identifier
        invalid_json_data = deepcopy(self.json_data)
        del invalid_json_data["identifier"]

        with self.assertRaises(Exception) as error:
            self.validator.validate(invalid_json_data)

        full_error_message = str(error.exception)
        actual_error_messages = full_error_message.replace("Validation errors: ", "").split("; ")
        self.assertIn("identifier is a mandatory field", actual_error_messages)

        # Test identifier is list of length 1
        valid_list_element = {
            "system": "https://supplierABC/identifiers/vacc",
            "value": "ACME-vacc123456",
        }
        ValidatorModelTests.test_list_value(
            self,
            field_location="identifier",
            valid_lists_to_test=[[valid_list_element]],
            predefined_list_length=1,
            valid_list_element=valid_list_element,
            is_list_of_dicts=True,
        )

    def test_pre_validate_identifier_value(self):
        """Test pre_validate_identifier_value accepts valid values and rejects invalid values"""
        valid_strings_to_test = [
            "e045626e-4dc5-4df3-bc35-da25263f901e",
            "ACME-vacc123456",
            "ACME-CUSTOMER1-vacc123456",
        ]
        ValidatorModelTests.test_string_value(
            self,
            field_location="identifier[0].value",
            valid_strings_to_test=valid_strings_to_test,
        )

    def test_pre_validate_identifier_system(self):
        """Test pre_validate_identifier_system accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_string_value(
            self,
            field_location="identifier[0].system",
            valid_strings_to_test=[
                "https://supplierABC/identifiers/vacc",
                "https://supplierABC/ODSCode_NKO41/identifiers/vacc",
            ],
        )

    def test_pre_validate_status(self):
        """Test pre_validate_status accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_string_value(
            self,
            field_location="status",
            valid_strings_to_test=["completed"],
            predefined_values=["completed"],
            invalid_strings_to_test=["1", "complete", "entered-in-error", "not-done"],
            is_mandatory_fhir=True,
        )

    def test_pre_validate_practitioner_name(self):
        """Test pre_validate_practitioner_name accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_list_value(
            self,
            field_location="contained[?(@.resourceType=='Practitioner')].name",
            valid_lists_to_test=[[{"family": "Test"}]],
            valid_list_element={"family": "Test"},
        )

    def test_pre_validate_practitioner_name_given(self):
        """Test pre_validate_practitioner_name_given accepts valid values and rejects invalid values"""
        valid_json_data = deepcopy(self.json_data)
        ValidatorModelTests.test_list_value(
            self,
            field_location=practitioner_name_given_field_location(valid_json_data),
            valid_lists_to_test=[["Test"], ["Test test"]],
            valid_list_element="Test",
            is_list_of_strings=True,
        )

    def test_pre_validate_practitioner_name_family(self):
        """Test pre_validate_practitioner_name_family accepts valid values and rejects invalid values"""
        valid_json_data = deepcopy(self.json_data)
        field_location = practitioner_name_family_field_location(valid_json_data)
        ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["test"])

    def test_pre_validate_recorded(self):
        """Test pre_validate_recorded accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_date_time_value(self, field_location="recorded", is_occurrence_date_time=False)

    def test_pre_validate_primary_source(self):
        """Test pre_validate_primary_source accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_boolean_value(self, field_location="primarySource")

    def test_pre_validate_extension(self):
        """Test pre_validate_extension accepts valid values and rejects invalid values for extension, valueCodeableConcept, and coding"""
        # Test case: missing "extension"
        invalid_json_data = deepcopy(self.json_data)
        del invalid_json_data["extension"]

        with self.assertRaises(Exception) as error:
            self.validator.validate(invalid_json_data)

        full_error_message = str(error.exception)
        actual_error_messages = full_error_message.replace("Validation errors: ", "").split("; ")
        self.assertIn("extension is a mandatory field", actual_error_messages)

    def test_pre_validate_missing_valueCodeableConcept(self):
        """Test pre_validate_extension  missing "valueCodeableConcept" within an extension"""
        # Test case: missing "valueCodeableConcept" within an extension
        invalid_json_data = deepcopy(self.json_data)
        del invalid_json_data["extension"][0]["valueCodeableConcept"]

        with self.assertRaises(Exception) as error:
            self.validator.validate(invalid_json_data)

        full_error_message = str(error.exception)
        actual_error_messages = full_error_message.replace("Validation errors: ", "").split("; ")
        self.assertIn("extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept is a mandatory field", actual_error_messages)

    def test_pre_validate_missing_valueCodeableConcept2(self):
        # Test case: missing "coding" within "valueCodeableConcept"
        invalid_json_data = deepcopy(self.json_data)
        del invalid_json_data["extension"][0]["valueCodeableConcept"]["coding"]

        with self.assertRaises(Exception) as error:
            self.validator.validate(invalid_json_data)

        full_error_message = str(error.exception)
        actual_error_messages = full_error_message.replace("Validation errors: ", "").split("; ")
        self.assertIn("extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding is a mandatory field", actual_error_messages)

    def test_pre_validate_missing_valueCodeableConcept3(self):
        # Test case: valid data (should not raise an exception)
        self.mock_redis_client.hget.return_value = "COVID19"
        valid_json_data = deepcopy(self.json_data)
        try:
            self.validator.validate(valid_json_data)
        except Exception as error:
            self.fail(f"Validation unexpectedly raised an exception: {error}")


    def test_pre_validate_extension_length(self):
        """Test test_pre_validate_extension_length accepts valid length of 1  and rejects invalid length for extension"""
        # Test case: missing "extension"
        invalid_json_data = deepcopy(self.json_data)
        invalid_json_data["extension"].append({
        "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
        "valueCodeableConcept": {
            "coding": [
            {
                "system": "http://snomed.info/sct",
                "code": "1324681000000101",
                "display": "Administration of first dose of severe acute respiratory syndrome coronavirus 2 vaccine (procedure)"
            }
            ]
        }
        })

        with self.assertRaises(Exception) as error:
            self.validator.validate(invalid_json_data)

        full_error_message = str(error.exception)
        actual_error_messages = full_error_message.replace("Validation errors: ", "").split("; ")
        self.assertIn("extension must be an array of length 1", actual_error_messages)

    def test_pre_validate_extension_url1(self):
        """Test test_pre_validate_extension_url accepts valid values and rejects invalid values for extension[0].url"""
        # Test case: missing "extension"
        invalid_json_data = deepcopy(self.json_data)
        invalid_json_data["extension"][0]["url"]='https://xyz/Extension-UKCore-VaccinationProcedure'

        with self.assertRaises(Exception) as error:
            self.validator.validate(invalid_json_data)

        full_error_message = str(error.exception)
        actual_error_messages = full_error_message.replace("Validation errors: ", "").split("; ")
        self.assertIn("extension[0].url must be one of the following: https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure", actual_error_messages)

    def test_pre_validate_extension_snomed_code(self):
        """Test test_pre_validate_extension_url accepts valid values and rejects invalid values for extension[0].url"""
        # Test case: missing "extension"
        invalid_json_data = deepcopy(self.json_data)
        test_values = ["12345abc", "12345", "1234567890123456789", "12345671", "1324681000000111"]
        for values in test_values:
            invalid_json_data["extension"][0]["valueCodeableConcept"]["coding"][0]["code"] = values

            with self.assertRaises(Exception) as error:
                self.validator.validate(invalid_json_data)

            full_error_message = str(error.exception)
            actual_error_messages = full_error_message.replace("Validation errors: ", "").split("; ")
            self.assertIn("extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].code is not a valid snomed code", actual_error_messages)

    def test_pre_validate_extension_to_extract_the_coding_code_value(self):
        "Test the array length for extension and it should be length 1"
        invalid_json_data = deepcopy(self.json_data)

        # Adding a new SNOMED code and testing if a specific code is retrieved
        invalid_json_data["extension"][0]["valueCodeableConcept"]["coding"].append({
            "system": "http://snomed.info/sct",
            "code": "1324681000000102",
            "display": "Administration of first dose of severe acute respiratory syndrome coronavirus 2 vaccine (procedure)"
        })
        actual_value = get_generic_extension_value(
            invalid_json_data,
            "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
            "http://snomed.info/sct",
            "code"
        )
        self.assertIn("1324681000000101", actual_value)

        # Updating system and adding another SNOMED code to verify the updated value
        invalid_json_data["extension"][0]["valueCodeableConcept"]["coding"][0]["system"] = "http://xyz.info/sct"
        invalid_json_data["extension"][0]["valueCodeableConcept"]["coding"].append({
            "system": "http://snomed.info/sct",
            "code": "1324681000000103",
            "display": "Administration of first dose of severe acute respiratory syndrome coronavirus 2 vaccine (procedure)"
        })
        actual_value = get_generic_extension_value(
            invalid_json_data,
            "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
            "http://snomed.info/sct",
            "code"
        )
        self.assertIn("1324681000000102", actual_value)

    def test_pre_validate_protocol_applied(self):
        """Test pre_validate_protocol_applied accepts valid values and rejects invalid values"""
        valid_list_element = {
            "targetDisease": [
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "6142004",
                            "display": "Influenza",
                        }
                    ]
                }
            ],
            "doseNumberPositiveInt": 1,
        }

        ValidatorModelTests.test_list_value(
            self,
            field_location="protocolApplied",
            valid_lists_to_test=[[valid_list_element]],
            predefined_list_length=1,
            valid_list_element=valid_list_element,
        )

    def test_pre_validate_protocol_applied_dose_number_positive_int(self):
        """
        Test pre_validate_protocol_applied_dose_number_positive_int accepts valid values and
        rejects invalid values
        """
        ValidatorModelTests.test_positive_integer_value(
            self,
            field_location="protocolApplied[0].doseNumberPositiveInt",
            valid_positive_integers_to_test=[1, 2, 3, 4, 5, 6, 7, 8, 9],
        )

    def test_pre_validate_protocol_applied_dose_number_string(self):
        """
        Test pre_validate_protocol_applied_dose_number_string accepts valid values and
        rejects invalid values
        """
        valid_json_data = deepcopy(self.json_data)
        valid_json_data["protocolApplied"][0]["doseNumberString"] = "Dose sequence not recorded"
        valid_json_data = parse("protocolApplied[0].doseNumberPositiveInt").filter(lambda d: True, valid_json_data)

        ValidatorModelTests.test_string_value(
            self,
            field_location="protocolApplied[0].doseNumberString",
            valid_strings_to_test=["Dose sequence not recorded"],
            valid_json_data=valid_json_data,
            defined_length="",
            invalid_strings_to_test=["Invalid"],
        )

    def test_pre_validate_target_disease(self):
        """Test pre_validate_target_disease accepts valid values and rejects invalid values"""

        valid_json_data = load_json_data(filename="completed_mmr_immunization_event.json")

        # Case: valid targetDisease
        self.assertIsNone(self.validator.validate(valid_json_data))

        # CASE: targetDisease absent
        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(valid_json_data),
            field_location="protocolApplied",
            invalid_value=[{"doseNumberPositiveInt": 1}],
            expected_error_message="protocolApplied[0].targetDisease is a mandatory field",
        )

        # CASE: targetDisease element missing 'coding' property
        invalid_target_disease = [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "14189004",
                        "display": "Measles",
                    }
                ]
            },
            {"text": "a_disease"},
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "36653000",
                        "display": "Rubella",
                    }
                ]
            },
        ]

        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(valid_json_data),
            field_location="protocolApplied[0].targetDisease",
            invalid_value=invalid_target_disease,
            expected_error_message="Every element of protocolApplied[0].targetDisease must have 'coding' property",
        )

    def test_pre_validate_target_disease_codings(self):
        """Test pre_validate_target_disease_codings accepts valid values and rejects invalid values"""
        field_location = "protocolApplied[0].targetDisease"

        # CASE: Valid target disease
        valid_target_disease_values = [
            [
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "14189004",
                            "display": "Measles",
                        },
                        {
                            "system": "some_other_system",
                            "code": "a_code",
                            "display": "Measles",
                        },
                    ]
                },
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "36989005",
                            "display": "Mumps",
                        }
                    ]
                },
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "36653000",
                            "display": "Rubella",
                        }
                    ]
                },
            ]
        ]

        _test_valid_values_accepted(
            self,
            valid_json_data=deepcopy(self.json_data),
            field_location=field_location,
            valid_values_to_test=valid_target_disease_values,
        )

        # CASE: Invalid target disease with two snomed codes in single coding element

        invalid_target_disease_value = [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "14189004",
                        "display": "Measles",
                    }
                ]
            },
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "36989005",
                        "display": "Mumps",
                    },
                    {
                        "system": "http://snomed.info/sct",
                        "code": "another_mumps_code",
                        "display": "Mumps",
                    },
                ]
            },
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "36653000",
                        "display": "Rubella",
                    }
                ]
            },
        ]

        # CASE: Invalid target disease with no snomed codes in one of the coding elements

        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(self.json_data),
            field_location=field_location,
            invalid_value=invalid_target_disease_value,
            expected_error_message="protocolApplied[0].targetDisease[1].coding must contain exactly one element "
            + "with a system of http://snomed.info/sct",
        )

        invalid_target_disease_value = [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "14189004",
                        "display": "Measles",
                    }
                ]
            },
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "36989005",
                        "display": "Mumps",
                    }
                ]
            },
            {
                "coding": [
                    {
                        "system": "some_other_system",
                        "code": "36653000",
                        "display": "Rubella",
                    }
                ]
            },
        ]

        _test_invalid_values_rejected(
            self,
            valid_json_data=deepcopy(self.json_data),
            field_location=field_location,
            invalid_value=invalid_target_disease_value,
            expected_error_message="protocolApplied[0].targetDisease[2].coding must contain exactly one element "
            + "with a system of http://snomed.info/sct",
        )

    def test_pre_validate_disease_type_coding_codes(self):
        """Test pre_validate_disease_type_coding_codes accepts valid values and rejects invalid values"""
        # Test data with single disease_type_coding_code
        ValidatorModelTests.test_string_value(
            self,
            field_location="protocolApplied[0].targetDisease[0]."
            + "coding[?(@.system=='http://snomed.info/sct')].code",
            valid_strings_to_test=[
                "840539006",
                "6142004",
                "240532009",
            ],
            valid_json_data=load_json_data(filename="completed_covid19_immunization_event.json"),
        )

        # Test data with multiple disease_type_coding_codes
        for i, disease_code in [
            (0, "14189004"),
            (1, "36989005"),
            (2, "36653000"),
        ]:
            ValidatorModelTests.test_string_value(
                self,
                field_location=f"protocolApplied[0].targetDisease[{i}]."
                + "coding[?(@.system=='http://snomed.info/sct')].code",
                valid_strings_to_test=[disease_code],
                valid_json_data=load_json_data(filename="completed_mmr_immunization_event.json"),
            )

    def test_pre_validate_manufacturer_display(self):
        """Test pre_validate_manufacturer_display accepts valid values and rejects invalid values"""
        field_location = "manufacturer.display"
        ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["dummy"])

    def test_pre_validate_lot_number(self):
        """Test pre_validate_lot_number accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_string_value(
            self,
            field_location="lotNumber",
            valid_strings_to_test=["sample", ValidValues.for_strings_with_any_length_chars],
            invalid_strings_to_test=["", None, 42, 3.889],
        )

    def test_pre_validate_expiration_date(self):
        """Test pre_validate_expiration_date accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_date_value(self, field_location="expirationDate")

    def test_pre_validate_site_coding(self):
        """Test pre_validate_site_coding accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_unique_list(
            self,
            field_location="site.coding",
            valid_lists_to_test=[[ValidValues.snomed_coding_element]],
            invalid_list_with_duplicates_to_test=[
                ValidValues.snomed_coding_element,
                ValidValues.snomed_coding_element,
            ],
            expected_error_message="site.coding[?(@.system=='http://snomed.info/sct')]" + " must be unique",
        )

    def test_pre_validate_site_coding_code(self):
        """Test pre_validate_site_coding_code accepts valid values and rejects invalid values"""
        field_location = "site.coding[?(@.system=='http://snomed.info/sct')].code"
        ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["dummy"])

    def test_pre_validate_site_coding_display(self):
        """Test pre_validate_site_coding_display accepts valid values and rejects invalid values"""
        field_location = "site.coding[?(@.system=='http://snomed.info/sct')].display"
        ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["dummy"])

    def test_pre_validate_route_coding(self):
        """Test pre_validate_route_coding accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_unique_list(
            self,
            field_location="route.coding",
            valid_lists_to_test=[[ValidValues.snomed_coding_element]],
            invalid_list_with_duplicates_to_test=[
                ValidValues.snomed_coding_element,
                ValidValues.snomed_coding_element,
            ],
            expected_error_message="route.coding[?(@.system=='http://snomed.info/sct')]" + " must be unique",
        )

    def test_pre_validate_route_coding_code(self):
        """Test pre_validate_route_coding_code accepts valid values and rejects invalid values"""
        field_location = "route.coding[?(@.system=='http://snomed.info/sct')].code"
        ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["dummy"])

    def test_pre_validate_route_coding_display(self):
        """Test pre_validate_route_coding_display accepts valid values and rejects invalid values"""
        field_location = "route.coding[?(@.system=='http://snomed.info/sct')].display"
        ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["dummy"])

    def test_pre_validate_dose_quantity_value(self):
        """Test pre_validate_dose_quantity_value accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_decimal_or_integer_value(
            self,
            field_location="doseQuantity.value",
            valid_decimals_and_integers_to_test=[
                1,  # small integer
                100,  # larger integer
                Decimal("1.0"),  # Only 0s after decimal point
                Decimal("0.1"),  # 1 decimal place
                Decimal("100.52"),  # 2 decimal places
                Decimal("32.430"),  # 3 decimal places
                Decimal("1.1234"),  # 4 decimal places,
                Decimal("1.123456789"),  # 9 decimal place
            ],
        )

    def test_pre_validate_dose_quantity_code(self):
        """Test pre_validate_dose_quantity_code accepts valid values and rejects invalid values"""
        field_location = "doseQuantity.code"
        ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["ABC123"])

    def test_pre_validate_dose_quantity_unit(self):
        """Test pre_validate_dose_quantity_unit accepts valid values and rejects invalid values"""
        field_location = "doseQuantity.unit"
        ValidatorModelTests.test_string_value(self, field_location, valid_strings_to_test=["Millilitre"])

    # TODO: ?add extra reason code to sample data for validation testing
    def test_pre_validate_reason_code_codings(self):
        """Test pre_validate_reason_code_codings accepts valid values and rejects invalid values"""
        # Check that both of the 2 reasonCode[{index}].coding fields in the sample data are rejected
        # when invalid
        for i in range(1):
            ValidatorModelTests.test_list_value(
                self,
                field_location=f"reasonCode[{i}].coding",
                valid_lists_to_test=[[{"code": "ABC123", "display": "test"}, {"code": "ABC123", "display": "test"}]],
                valid_list_element={"code": "ABC123", "display": "test"},
            )

    # TODO: ?add extra reason code to sample data for validation testing
    def test_pre_validate_reason_code_coding_codes(self):
        """Test pre_validate_reason_code_coding_codes accepts valid values and rejects invalid values"""
        # Check that both of the reasonCode[{index}].coding[0].code fields in the sample data are
        # rejected when invalid
        for i in range(1):
            ValidatorModelTests.test_string_value(
                self,
                field_location=f"reasonCode[{i}].coding[0].code",
                valid_strings_to_test=["ABC123"],
            )

    def test_pre_validate_organisation_identifier_system(self):
        """Test pre_validate_organization_identifier_system accepts valid systems and rejects invalid systems"""
        ValidatorModelTests.test_string_value(
            self,
            field_location="performer[?(@.actor.type=='Organization')].actor.identifier.system",
            valid_strings_to_test=["DUMMY"],
        )

    def test_pre_validate_location_identifier_value(self):
        """Test pre_validate_location_identifier_value accepts valid values and rejects invalid values"""
        ValidatorModelTests.test_string_value(
            self,
            field_location="location.identifier.value",
            valid_strings_to_test=["B0C4P", "140565"],
        )

    def test_pre_validate_location_identifier_system(self):
        """Test pre_validate_location_identifier_system accepts valid values and rejects invalid values"""
        field_location = "location.identifier.system"
        ValidatorModelTests.test_string_value(
            self,
            field_location,
            valid_strings_to_test=["https://fhir.hl7.org.uk/Id/140565"],
        )


class TestImmunizationModelPreValidationRulesForReduceValidation(unittest.TestCase):
    """Test immunization pre validation rules on the FHIR model using the status="reduce validation" data"""

    def setUp(self):
        """Set up for each test. This runs before every test"""
        self.json_data = load_json_data("reduce_validation_hpv_immunization_event.json")
        self.validator = ImmunizationValidator(add_post_validators=False)
