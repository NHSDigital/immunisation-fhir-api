
from decimal import Decimal
from utils.base_test import ImmunizationBaseTest
from utils.constants import valid_nhs_number1

from utils.resource import generate_imms_resource, generate_filtered_imms_resource
from utils.mappings import VaccineTypes
from lib.env import get_service_base_path


class TestSearchImmunizationByIdentifier(ImmunizationBaseTest):

    def store_records(self, *resources):
        ids = []
        for res in resources:
            imms_id = self.default_imms_api.create_immunization_resource(res)
            ids.append(imms_id)
        return ids[0] if len(ids) == 1 else tuple(ids)

    def test_search_imms(self):
        """it should search records given nhs-number and vaccine type"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                # Given two patients each with one covid_19
                covid_19_p1 = generate_imms_resource()
                rsv_p1 = generate_imms_resource()
                covid_ids = self.store_records(covid_19_p1)
                rsv_ids = self.store_records(rsv_p1)

                # Retrieve the resources to get the identifier system and value via read API
                covid_resource = imms_api.get_immunization_by_id(covid_ids).json()
                rsv_resource = imms_api.get_immunization_by_id(rsv_ids).json()

                # Extract identifier components safely for covid resource
                identifiers = covid_resource.get("identifier", [])
                identifier_system = identifiers[0].get("system")
                identifier_value = identifiers[0].get("value")

                # Extract identifier components safely for rsv resource
                rsv_identifiers = rsv_resource.get("identifier", [])
                rsv_identifier_system = rsv_identifiers[0].get("system")
                rsv_identifier_value = rsv_identifiers[0].get("value")

                # When
                search_response = imms_api.search_immunization_by_identifier(identifier_system, identifier_value)
                self.assertEqual(search_response.status_code, 200, search_response.text)
                bundle = search_response.json()
                self.assertEqual(bundle.get("resourceType"), "Bundle", bundle)
                entries = bundle.get("entry", [])
                self.assertTrue(entries, "Expected at least one match in Bundle.entry")
                self.assertEqual(len(entries), 1, f"Expected exactly one match, got {len(entries)}")

                # When
                rsv_search_response = imms_api.search_immunization_by_identifier(
                    rsv_identifier_system,
                    rsv_identifier_value
                    )
                self.assertEqual(rsv_search_response.status_code, 200, search_response.text)
                rsv_bundle = rsv_search_response.json()
                self.assertEqual(bundle.get("resourceType"), "Bundle", rsv_bundle)
                entries = rsv_bundle.get("entry", [])
                self.assertTrue(entries, "Expected at least one match in Bundle.entry")
                self.assertEqual(len(entries), 1, f"Expected exactly one match, got {len(entries)}")

    def test_search_backwards_compatible(self):
        """Test that SEARCH 200 response body is backwards compatible with Immunisation History FHIR API.
        This test proves that the search endpoint’s response is still shaped exactly like the
        Immunisation History FHIR API expects (“backwards compatible”), not just that it returns a 200
        """
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):

                stored_imms_resource = generate_imms_resource()
                imms_identifier_value = stored_imms_resource["identifier"][0]["value"]
                imms_id = self.store_records(stored_imms_resource)

                # Prepare the imms resource expected from the response. Note that id and identifier_value need to be
                # updated to match those assigned by the create_an_imms_obj and store_records functions.
                expected_imms_resource = generate_filtered_imms_resource(
                    crud_operation_to_filter_for="SEARCH",
                    imms_identifier_value=imms_identifier_value,
                    nhs_number=valid_nhs_number1,
                    vaccine_type=VaccineTypes.covid_19,
                )
                expected_imms_resource["id"] = imms_id
                expected_imms_resource["meta"] = {"versionId": "1"}

                # Retrieve the resource to get the identifier system and value via READ API
                imms_resource = imms_api.get_immunization_by_id(imms_id).json()
                identifiers = imms_resource.get("identifier", [])
                identifier_system = identifiers[0].get("system")
                identifier_value = identifiers[0].get("value")
                self.assertIsNotNone(identifier_system, "Identifier system is None")
                self.assertIsNotNone(identifier_value, "Identifier value is None")

                # When
                response = imms_api.search_immunization_by_identifier(identifier_system, identifier_value)

                # Then
                self.assertEqual(response.status_code, 200, response.text)
                body = response.json(parse_float=Decimal)
                entries = body["entry"]
                response_imms = [item for item in entries if item["resource"]["resourceType"] == "Immunization"]
                response_patients = [item for item in entries if item["resource"]["resourceType"] == "Patient"]
                response_other_entries = [
                    item for item in entries if item["resource"]["resourceType"] not in ("Patient", "Immunization")
                ]

                # Check bundle structure apart from entry
                self.assertEqual(body["resourceType"], "Bundle")
                self.assertEqual(body["type"], "searchset")
                self.assertEqual(body["total"], len(response_imms))

                # Check that entry only contains a patient and immunizations
                self.assertEqual(len(response_other_entries), 0)
                self.assertEqual(len(response_patients), 0)

                # Check Immunization structure
                for entry in response_imms:
                    self.assertEqual(entry["search"], {"mode": "match"})
                    self.assertTrue(entry["fullUrl"].startswith("https://"))
                    self.assertEqual(entry["resource"]["resourceType"], "Immunization")
                    imms_identifier = entry["resource"]["identifier"]
                    self.assertEqual(len(imms_identifier), 1, "Immunization did not have exactly 1 identifier")
                    self.assertEqual(imms_identifier[0]["system"], identifier_system)
                    self.assertEqual(imms_identifier[0]["value"], identifier_value)

                # Check structure of one of the imms resources
                response_imm = next(item for item in entries if item["resource"]["id"] == imms_id)
                self.assertEqual(
                    response_imm["fullUrl"], f"{get_service_base_path()}/Immunization/{imms_id}"
                )
                self.assertEqual(response_imm["search"], {"mode": "match"})
                expected_imms_resource["patient"]["reference"] = response_imm["resource"]["patient"]["reference"]
                self.assertEqual(response_imm["resource"], expected_imms_resource)
