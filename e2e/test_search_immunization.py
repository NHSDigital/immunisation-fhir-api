import datetime
import pprint
import uuid
from typing import NamedTuple, Literal, Optional, List
from decimal import Decimal

from utils.base_test import ImmunizationBaseTest
from utils.constants import valid_nhs_number1, valid_nhs_number2, valid_patient_identifier2, valid_patient_identifier1
from utils.resource import create_an_imms_obj, create_a_filtered_imms_obj
from utils.mappings import VaccineTypes


class TestSearchImmunization(ImmunizationBaseTest):
    # NOTE: In each test, the result may contain more hits. We only assert if the resource that we created is
    #  in the result set and assert the one that we don't expect is not present.
    # This is to make these tests stateless otherwise; we need to clean up the db after each test

    def store_records(self, *resources):
        for res in resources:
            imms_id = self.create_immunization_resource(self.default_imms_api, res)
            res["id"] = imms_id

    def test_search_imms(self):
        """it should search records given nhs-number and vaccine type"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                # Given two patients each with one covid_19
                covid_19_p1 = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, VaccineTypes.covid_19)
                covid_19_p2 = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number2, VaccineTypes.covid_19)
                self.store_records(covid_19_p1, covid_19_p2)

                # When
                response = imms_api.search_immunizations(valid_nhs_number1, VaccineTypes.covid_19)

                # Then
                self.assertEqual(response.status_code, 200, response.text)
                body = response.json()
                self.assertEqual(body["resourceType"], "Bundle")

                resource_ids = [entity["resource"]["id"] for entity in body["entry"]]
                self.assertTrue(covid_19_p1["id"] in resource_ids)
                self.assertTrue(covid_19_p2["id"] not in resource_ids)

    def test_search_patient_multiple_diseases(self):
        # Given patient has two vaccines
        covid_19 = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, VaccineTypes.covid_19)
        flu = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, VaccineTypes.flu)
        self.store_records(covid_19, flu)

        # When
        response = self.default_imms_api.search_immunizations(valid_nhs_number1, VaccineTypes.covid_19)
        print(f"response_search:{response}")
        # Then
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()

        resource_ids = [entity["resource"]["id"] for entity in body["entry"]]
        self.assertIn(covid_19["id"], resource_ids)
        self.assertNotIn(flu["id"], resource_ids)

    def test_search_backwards_compatible(self):
        """Test that SEARCH 200 response body is backwards compatible with Immunisation History FHIR API"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                # Given that the patient has a covid_19 vaccine event stored in the IEDS
                stored_imms_resource = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, VaccineTypes.covid_19)
                imms_identifier_value = stored_imms_resource["identifier"][0]["value"]
                self.store_records(stored_imms_resource)
                imms_id = stored_imms_resource["id"]

                # Prepare the imms resource expected from the response. Note that id and identifier_value need to be
                # updated to match those assigned by the create_an_imms_obj and store_records functions.
                expected_imms_resource = create_a_filtered_imms_obj(
                    crud_operation_to_filter_for="SEARCH",
                    imms_id=imms_id,
                    imms_identifier_value=imms_identifier_value,
                    nhs_number=valid_nhs_number1,
                    vaccine_type=VaccineTypes.covid_19,
                )

                # When
                response = imms_api.search_immunizations(valid_nhs_number1, VaccineTypes.covid_19)

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
                self.assertEqual(len(response_patients), 1)

                # Check patient structure
                response_patient = response_patients[0]
                self.assertEqual(response_patient["search"], {"mode": "include"})
                self.assertTrue(response_patient["fullUrl"].startswith("urn:uuid:"))
                self.assertTrue(uuid.UUID(response_patient["fullUrl"].split(":")[2]))
                expected_patient_resource_keys = ["resourceType", "id", "identifier", "birthDate"]
                self.assertEqual(sorted(response_patient["resource"].keys()), sorted(expected_patient_resource_keys))
                self.assertEqual(response_patient["resource"]["id"], valid_nhs_number1)
                patient_identifier = response_patient["resource"]["identifier"]
                # NOTE: If PDS response ever changes to send more than one identifier then the below will break
                self.assertEqual(len(patient_identifier), 1)
                self.assertEqual(sorted(patient_identifier[0].keys()), sorted(["system", "value"]))
                self.assertEqual(patient_identifier[0]["system"], "https://fhir.nhs.uk/Id/nhs-number")
                self.assertEqual(patient_identifier[0]["value"], valid_nhs_number1)

                # Check structure of one of the imms resources
                expected_imms_resource["patient"]["reference"] = response_patient["fullUrl"]
                response_imm = next(item for item in entries if item["resource"]["id"] == imms_id)
                self.assertEqual(
                    response_imm["fullUrl"], f"https://api.service.nhs.uk/immunisation-fhir-api/Immunization/{imms_id}"
                )
                self.assertEqual(response_imm["search"], {"mode": "match"})
                self.assertEqual(response_imm["resource"], expected_imms_resource)

    def test_search_ignore_deleted(self):
        # Given patient has three vaccines and the last one is deleted
        mmr1 = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, VaccineTypes.mmr)
        mmr2 = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, VaccineTypes.mmr)
        self.store_records(mmr1, mmr2)

        to_delete_mmr = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, VaccineTypes.mmr)
        deleted_mmr = self.create_a_deleted_immunization_resource(self.default_imms_api, to_delete_mmr)

        # When
        response = self.default_imms_api.search_immunizations(valid_nhs_number1, VaccineTypes.mmr)

        # Then
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()

        resource_ids = [entity["resource"]["id"] for entity in body["entry"]]
        self.assertTrue(mmr1["id"] in resource_ids)
        self.assertTrue(mmr2["id"] in resource_ids)
        self.assertTrue(deleted_mmr["id"] not in resource_ids)

    def test_search_immunization_parameter_smoke_tests(self):
        time_1 = "2024-01-30T13:28:17.271+00:00"
        time_2 = "2024-02-01T13:28:17.271+00:00"
        stored_records = [
            create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, VaccineTypes.mmr),
            create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, VaccineTypes.flu),
            create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, VaccineTypes.covid_19),
            create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, VaccineTypes.covid_19, time_1),
            create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, VaccineTypes.covid_19, time_2),
            create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number2, VaccineTypes.flu),
            create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number2, VaccineTypes.covid_19),
        ]

        self.store_records(*stored_records)
        created_resource_ids = [result["id"] for result in stored_records]

        # When
        class SearchTestParams(NamedTuple):
            method: Literal["POST", "GET"]
            query_string: Optional[str]
            body: Optional[str]
            should_be_success: bool
            expected_indexes: List[int]

        searches = [
            SearchTestParams("GET", "", None, False, []),
            # No results.
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier2}&-immunization.target={VaccineTypes.mmr}",
                None,
                True,
                [],
            ),
            # Basic success.
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target={VaccineTypes.mmr}",
                None,
                True,
                [0],
            ),
            # "Or" params.
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target={VaccineTypes.mmr},"
                + f"{VaccineTypes.flu}",
                None,
                True,
                [0, 1],
            ),
            # GET does not support body.
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target={VaccineTypes.mmr}",
                f"patient.identifier={valid_patient_identifier1}",
                True,
                [0],
            ),
            SearchTestParams(
                "POST",
                None,
                f"patient.identifier={valid_patient_identifier1}&-immunization.target={VaccineTypes.mmr}",
                True,
                [0],
            ),
            # Duplicated NHS number not allowed, spread across query and content.
            SearchTestParams(
                "POST",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target={VaccineTypes.mmr}",
                f"patient.identifier={valid_patient_identifier1}",
                False,
                [],
            ),
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}"
                f"&patient.identifier={valid_patient_identifier1}"
                f"&-immunization.target={VaccineTypes.mmr}",
                None,
                False,
                [],
            ),
            # "And" params not supported.
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target={VaccineTypes.mmr}"
                f"&-immunization.target={VaccineTypes.flu}",
                None,
                False,
                [],
            ),
            # Date
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target={VaccineTypes.covid_19}",
                None,
                True,
                [2, 3, 4],
            ),
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target={VaccineTypes.covid_19}"
                f"&-date.from=2024-01-30",
                None,
                True,
                [3, 4],
            ),
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target={VaccineTypes.covid_19}"
                f"&-date.to=2024-01-30",
                None,
                True,
                [2, 3],
            ),
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target={VaccineTypes.covid_19}"
                f"&-date.from=2024-01-01&-date.to=2024-01-30",
                None,
                True,
                [3],
            ),
            # "from" after "to" is an error.
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target={VaccineTypes.covid_19}"
                f"&-date.from=2024-02-01&-date.to=2024-01-30",
                None,
                False,
                [0],
            ),
        ]

        for search in searches:
            pprint.pprint(search)
            response = self.default_imms_api.search_immunizations_full(search.method, search.query_string, search.body)

            # Then
            assert response.ok == search.should_be_success, response.text

            results: dict = response.json()
            if search.should_be_success:
                assert "entry" in results.keys()
                assert response.status_code == 200
                assert results["resourceType"] == "Bundle"

                result_ids = [result["resource"]["id"] for result in results["entry"]]
                created_and_returned_ids = list(set(result_ids) & set(created_resource_ids))
                assert len(created_and_returned_ids) == len(search.expected_indexes)
                for expected_index in search.expected_indexes:
                    assert created_resource_ids[expected_index] in result_ids

    def test_search_immunization_accepts_include_and_provides_patient(self):
        """it should accept the _include parameter of "Immunization:patient" and return the patient."""

        # Arrange
        imms_obj = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, VaccineTypes.mmr)
        self.store_records(imms_obj)

        response = self.default_imms_api.search_immunizations_full(
            "POST",
            f"patient.identifier={valid_patient_identifier1}&-immunization.target={VaccineTypes.mmr}"
            + "&_include=Immunization:patient",
            None,
        )

        assert response.ok
        result = response.json()
        entries = result["entry"]

        entry_ids = [result["resource"]["id"] for result in result["entry"]]
        assert imms_obj["id"] in entry_ids

        patient_entry = next(entry for entry in entries if entry["resource"]["resourceType"] == "Patient")
        assert patient_entry["search"]["mode"] == "include"

        assert patient_entry["resource"]["identifier"][0]["system"] == "https://fhir.nhs.uk/Id/nhs-number"
        assert patient_entry["resource"]["identifier"][0]["value"] == valid_nhs_number1

        datetime.datetime.strptime(patient_entry["resource"]["birthDate"], "%Y-%m-%d").date()

        response_without_include = self.default_imms_api.search_immunizations_full(
            "POST", f"patient.identifier={valid_patient_identifier1}&-immunization.target={VaccineTypes.mmr}", None
        )

        assert response_without_include.ok
        result_without_include = response_without_include.json()

        # Matches Immunisation History API in that it doesn't matter if you don't pass "_include".

        # Ignore link, patient full url and immunisation patient reference as these will always differ.
        result["link"] = []
        result_without_include["link"] = []

        for entry in result["entry"]:
            if entry["resource"]["resourceType"] == "Immunization":
                entry["resource"]["patient"]["reference"] = "MOCK VALUE"
            elif entry["resource"]["resourceType"] == "Patient":
                entry["fullUrl"] = "MOCK VALUE"

        for entry in result_without_include["entry"]:
            if entry["resource"]["resourceType"] == "Immunization":
                entry["resource"]["patient"]["reference"] = "MOCK VALUE"
            elif entry["resource"]["resourceType"] == "Patient":
                entry["fullUrl"] = "MOCK VALUE"

        self.assertEqual(result, result_without_include)

    def test_search_reject_tbc(self):
        # Given patient has a vaccine with no NHS number
        imms = create_an_imms_obj(str(uuid.uuid4()), "TBC", VaccineTypes.mmr)
        del imms["contained"][1]["identifier"][0]["value"]
        self.store_records(imms)

        # When
        response = self.default_imms_api.search_immunizations("TBC", f"{VaccineTypes.mmr}")

        # Then
        self.assert_operation_outcome(response, 400)
