from utils.base_test import ImmunizationBaseTest
from lib.env import get_service_base_path
import pprint
import uuid
from utils.constants import valid_nhs_number1
from utils.resource import generate_imms_resource
from utils.mappings import VaccineTypes
from typing import NamedTuple, Literal, Optional


class TestSearchImmunizationByIdentifier(ImmunizationBaseTest):

    def store_records(self, *resources):
        ids = []
        for res in resources:
            imms_id = self.default_imms_api.create_immunization_resource(res)
            ids.append(imms_id)
        return ids[0] if len(ids) == 1 else tuple(ids)

    def test_search_imms(self):
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                covid_19_p1 = generate_imms_resource()
                covid_ids = self.store_records(covid_19_p1)

                # Retrieve the resources to get the identifier system and value via read API
                covid_resource = imms_api.get_immunization_by_id(covid_ids).json()

                # Extract identifier components safely for covid resource
                identifiers = covid_resource.get("identifier", [])
                identifier_system = identifiers[0].get("system")
                identifier_value = identifiers[0].get("value")

                # When
                search_response = imms_api.search_immunization_by_identifier_and_elements(
                    identifier_system, identifier_value)
                self.assertEqual(search_response.status_code, 200, search_response.text)
                bundle = search_response.json()
                self.assertEqual(bundle.get("resourceType"), "Bundle", bundle)
                entries = bundle.get("entry", [])
                self.assertTrue(entries, "Expected at least one match in Bundle.entry")
                self.assertEqual(len(entries), 1, f"Expected exactly one match, got {len(entries)}")
                self.assertIn("meta", entries[0]["resource"])
                self.assertEqual(entries[0]["resource"]["id"], covid_ids)
                self.assertEqual(entries[0]["resource"]["meta"]["versionId"], 1)
                self.assertTrue(entries[0]["fullUrl"].startswith("https://"))
                self.assertEqual(
                    entries[0]["fullUrl"], f"{get_service_base_path()}/Immunization/{covid_ids}"
                )

    def test_search_imms_no_match_returns_empty_bundle(self):
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                resp = imms_api.search_immunization_by_identifier_and_elements(
                    "http://example.org/sys", "does-not-exist-123"
                )
                self.assertEqual(resp.status_code, 200, resp.text)
                bundle = resp.json()
                self.assertEqual(bundle.get("resourceType"), "Bundle", bundle)
                self.assertEqual(bundle.get("type"), "searchset")
                self.assertEqual(bundle.get("total", 0), 0)
                self.assertFalse(bundle.get("entry"))

    def test_search_immunization_parameter_smoke_tests(self):
        stored_records = generate_imms_resource(
            valid_nhs_number1, VaccineTypes.covid_19,
            imms_identifier_value=str(uuid.uuid4()))

        imms_id = self.store_records(stored_records)
        # Retrieve the resources to get the identifier system and value via read API
        covid_resource = self.default_imms_api.get_immunization_by_id(imms_id).json()

        # Extract identifier components safely for covid resource
        identifiers = covid_resource.get("identifier", [])
        identifier_system = identifiers[0].get("system")
        identifier_value = identifiers[0].get("value")

        # created_resource_ids = [result["id"] for result in stored_records]

        class SearchTestParams(NamedTuple):
            method: Literal["POST", "GET"]
            query_string: Optional[str]
            body: Optional[str]
            should_be_success: bool
            expected_status_code: int = 200

        searches = [
                SearchTestParams(
                    "GET",
                    "",
                    None,
                    False,
                    400
                ),
                # No results.
                SearchTestParams(
                    "GET",
                    f"identifier={identifier_system}|{identifier_value}",
                    None,
                    True,
                    200
                ),
                SearchTestParams(
                    "POST",
                    f"identifier={identifier_system}|{identifier_value}&_elements=id,meta",
                    None,
                    True,
                    200
                )
                ]
        for search in searches:
            pprint.pprint(search)
            response = self.default_imms_api.search_immunizations_full(
                search.method, search.query_string,
                body=search.body,
                expected_status_code=search.expected_status_code)

            # Then
            assert response.ok == search.should_be_success, response.text

            results: dict = response.json()
            if search.should_be_success:
                assert "entry" in results.keys()
                assert response.status_code == 200
                assert results["resourceType"] == "Bundle"

                # result_ids = [result["resource"]["id"] for result in results["entry"]]
                # created_and_returned_ids = list(set(result_ids) & set(created_resource_ids))
                # assert len(created_and_returned_ids) == len(search.expected_indexes)
                # for expected_index in search.expected_indexes:
                # assert created_resource_ids[expected_index] in result_ids
