"""Tests for Filter class"""

from copy import deepcopy
from uuid import uuid4

import unittest

from src.constants import Urls
from src.filter import (
    Filter,
    remove_reference_to_contained_practitioner,
    create_reference_to_patient_resource,
    add_use_to_identifier,
    replace_address_postal_codes,
    replace_organization_values,
)
from tests.utils.generic_utils import load_json_data


class TestFilter(unittest.TestCase):
    """Test for Filter class"""

    def setUp(self):
        self.covid_19_immunization_event = load_json_data("completed_covid19_immunization_event.json")
        self.bundle_patient_resource = load_json_data("bundle_patient_resource.json")

    def test_remove_reference_to_contained_practitioner(self):
        """Tests to ensure remove_refernce_to_contained_practitioner correctly removes the reference"""

        # TEST CASE: contained practitioner exists
        input_data = {
            "resourceType": "Immunization",
            "contained": [
                {"resourceType": "Patient", "id": "Pat1"},
                {"resourceType": "Practitioner", "id": "Pract1"},
            ],
            "performer": [
                {"actor": {"type": "Organization"}},
                {"actor": {"reference": "#Pract1"}},
                {"actor": {"reference": "NOT AN INTERNAL REFERENCE"}},
            ],
        }

        expected_output = {
            "resourceType": "Immunization",
            "contained": [
                {"resourceType": "Patient", "id": "Pat1"},
                {"resourceType": "Practitioner", "id": "Pract1"},
            ],
            "performer": [
                {"actor": {"type": "Organization"}},
                {"actor": {"reference": "NOT AN INTERNAL REFERENCE"}},
            ],
        }

        self.assertEqual(remove_reference_to_contained_practitioner(input_data), expected_output)

        # TEST CASE: contained practitioner does not exist
        input_data = {
            "resourceType": "Immunization",
            "contained": [{"resourceType": "Patient", "id": "Pat1"}],
            "performer": [
                {"actor": {"type": "Organization"}},
                {"actor": {"reference": "NOT AN INTERNAL REFERENCE"}},
            ],
        }

        expected_output = deepcopy(input_data)

        self.assertEqual(remove_reference_to_contained_practitioner(input_data), expected_output)

    def test_create_reference_to_patient_resource(self):
        """Test that create_reference_to_patient_resource creates an appropriate patient reference"""
        input_data = deepcopy(self.bundle_patient_resource)
        patient_uuid = str(uuid4())
        expected_output = {
            "reference": patient_uuid,
            "type": "Patient",
            "identifier": {"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9000000009"},
        }

        self.assertEqual(create_reference_to_patient_resource(patient_uuid, input_data), expected_output)

    def test_add_use_to_identifier(self):
        """Test that a use of "offical" is added to identifier[0] is no use already given"""
        input_data = deepcopy(self.covid_19_immunization_event)
        excepted_output = deepcopy(self.covid_19_immunization_event)
        excepted_output["identifier"][0]["use"] = "official"

        self.assertEqual(add_use_to_identifier(input_data), excepted_output)

    def test_replace_address_postal_codes(self):
        """Test that replace_address_postal_codes replaces the postal codes and leaves all other data unaltered"""
        input_imms = load_json_data("completed_covid19_immunization_event.json")
        expected_output = deepcopy(input_imms)
        expected_output["contained"][1]["address"][0]["postalCode"] = "ZZ99 3CZ"
        self.assertEqual(replace_address_postal_codes(input_imms), expected_output)

    def test_replace_organization_values(self):
        """
        Test that replace_organziation_values replaces the relevant organization values and leave all other data
        unaltered
        """
        # Prepare the input data
        input_imms = load_json_data("completed_covid19_immunization_event.json")
        # Change the input data's organization_identifier_system to be something other than the ods url
        input_imms["performer"][1]["actor"]["identifier"]["system"] = Urls.urn_school_number
        # Add organization_display to the input data (note that whilst this field is not one of the expected fields,
        # the validator does not prevent it from being included on a create or update, so the possiblity of it
        # existing must be handled)
        input_imms["performer"][1]["actor"]["display"] = "test"

        # Prepare expected output data
        expected_output = deepcopy(input_imms)
        del expected_output["performer"][1]["actor"]["display"]

        # TEST CASE: Input data has organization identifier value and system
        input_imms_data = deepcopy(input_imms)
        expected_output_data = deepcopy(expected_output)
        expected_organization_identifier = {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "N2N9I"}
        expected_output_data["performer"][1]["actor"]["identifier"] = expected_organization_identifier
        self.assertEqual(replace_organization_values(deepcopy(input_imms)), expected_output_data)

        # TEST CASE: Input data has organization identifier value, does not have organization identifier system
        input_imms_data = deepcopy(input_imms)
        del input_imms_data["performer"][1]["actor"]["identifier"]["system"]
        expected_output_data = deepcopy(expected_output)
        expected_organization_identifier = {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "N2N9I"}
        expected_output_data["performer"][1]["actor"]["identifier"] = expected_organization_identifier
        self.assertEqual(replace_organization_values(input_imms_data), expected_output_data)

        # TEST CASE: Input data does not have organization identifier system, does have organization identifier value
        input_imms_data = deepcopy(input_imms)
        del input_imms_data["performer"][1]["actor"]["identifier"]["value"]
        expected_output_data = deepcopy(expected_output)
        expected_organization_identifier = {"system": "https://fhir.nhs.uk/Id/ods-organization-code"}
        expected_output_data["performer"][1]["actor"]["identifier"] = expected_organization_identifier
        self.assertEqual(replace_organization_values(input_imms_data), expected_output_data)

        # TEST CASE: Input data does not have organization identifier system or value
        input_imms_data = deepcopy(input_imms)
        del input_imms_data["performer"][1]["actor"]["identifier"]
        expected_output_data = deepcopy(expected_output)
        del expected_output_data["performer"][1]["actor"]["identifier"]
        self.assertEqual(replace_organization_values(input_imms_data), expected_output_data)

    def test_filter_search(self):
        """Tests to ensure Filter.search appropriately filters a FHIR Immunization Resource"""
        patient_full_url = f"urn:uuid:{str(uuid4())}"
        unfiltered_imms = deepcopy(self.covid_19_immunization_event)
        expected_output = load_json_data(
            "completed_covid19_immunization_event_filtered_for_search_using_bundle_patient_resource.json"
        )
        expected_output["patient"]["reference"] = patient_full_url

        self.assertEqual(Filter.search(unfiltered_imms, patient_full_url), expected_output)