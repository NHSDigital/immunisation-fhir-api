from utils.base_test import ImmunizationBaseTest
from utils.resource import generate_imms_resource
from lib.env import get_service_base_path


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
