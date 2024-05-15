import datetime
import pprint
import uuid
from typing import NamedTuple, Literal, Optional, List

from utils.base_test import ImmunizationBaseTest
from utils.constants import valid_nhs_number1, valid_nhs_number2, valid_patient_identifier2, valid_patient_identifier1
from utils.resource import create_an_imms_obj
from utils.mappings import VaccineTypes


class TestSearchImmunization(ImmunizationBaseTest):
    # NOTE: In each test, the result may contain more hits. We only assert if the resource that we created is
    #  in the result set and assert the one that we don't expect is not present.
    #  This is to make these tests stateless otherwise; we need to clean up the db after each test

    def store_records(self, *resources):
        for res in resources:
            imms_id = self.create_immunization_resource(self.default_imms_api, res)
            res["id"] = imms_id

    def test_search_imms(self):
        """it should search records given nhs-number and vaccine type"""
        for imms_api in self.imms_apis:
            with self.subTest(imms_api):
                # Given two patients each with one mmr
                # TODO: BUG Check why mmr_p2 has flu vaccine type
                mmr_p1 = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, VaccineTypes.mmr)
                mmr_p2 = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number2, VaccineTypes.flu)
                self.store_records(mmr_p1, mmr_p2)

                # When
                response = imms_api.search_immunizations(valid_nhs_number1, VaccineTypes.mmr)

                # Then
                self.assertEqual(response.status_code, 200, response.text)
                body = response.json()
                self.assertEqual(body["resourceType"], "Bundle")

                resource_ids = [entity["resource"]["id"] for entity in body["entry"]]
                self.assertTrue(mmr_p1["id"] in resource_ids)
                self.assertTrue(mmr_p2["id"] not in resource_ids)

    def test_search_patient_multiple_diseases(self):
        # TODO: BUG Is this test a duplicate of the above?
        # Given patient has two vaccines
        mmr = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, VaccineTypes.mmr)
        flu = create_an_imms_obj(str(uuid.uuid4()), valid_nhs_number1, VaccineTypes.flu)
        self.store_records(mmr, flu)

        # When
        response = self.default_imms_api.search_immunizations(valid_nhs_number1, VaccineTypes.mmr)

        # Then
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()

        resource_ids = [entity["resource"]["id"] for entity in body["entry"]]
        self.assertIn(mmr["id"], resource_ids)
        self.assertNotIn(flu["id"], resource_ids)

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

        # TODO: VACCINE_TYPE Amend these searches to  use vaccine type enums
        searches = [
            SearchTestParams("GET", "", None, False, []),
            # No results.
            SearchTestParams(
                "GET", f"patient.identifier={valid_patient_identifier2}&-immunization.target=MMR", None, True, []
            ),
            # Basic success.
            SearchTestParams(
                "GET", f"patient.identifier={valid_patient_identifier1}&-immunization.target=MMR", None, True, [0]
            ),
            # "Or" params.
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target=MMR,FLU",
                None,
                True,
                [0, 1],
            ),
            # GET does not support body.
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target=MMR",
                f"patient.identifier={valid_patient_identifier1}",
                True,
                [0],
            ),
            SearchTestParams(
                "POST", None, f"patient.identifier={valid_patient_identifier1}&-immunization.target=MMR", True, [0]
            ),
            # Duplicated NHS number not allowed, spread across query and content.
            SearchTestParams(
                "POST",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target=MMR",
                f"patient.identifier={valid_patient_identifier1}",
                False,
                [],
            ),
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}"
                f"&patient.identifier={valid_patient_identifier1}"
                f"&-immunization.target=MMR",
                None,
                False,
                [],
            ),
            # "And" params not supported.
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target=MMR" f"&-immunization.target=FLU",
                None,
                False,
                [],
            ),
            # Date
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target=COVID19",
                None,
                True,
                [2, 3, 4],
            ),
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target=COVID19"
                f"&-date.from=2024-01-30",
                None,
                True,
                [3, 4],
            ),
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target=COVID19" f"&-date.to=2024-01-30",
                None,
                True,
                [2, 3],
            ),
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target=COVID19"
                f"&-date.from=2024-01-01&-date.to=2024-01-30",
                None,
                True,
                [3],
            ),
            # "from" after "to" is an error.
            SearchTestParams(
                "GET",
                f"patient.identifier={valid_patient_identifier1}&-immunization.target=COVID19"
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
            f"patient.identifier={valid_patient_identifier1}&-immunization.target=MMR&_include=Immunization:patient",
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
            "POST", f"patient.identifier={valid_patient_identifier1}&-immunization.target=MMR", None
        )

        assert response_without_include.ok
        result_without_include = response_without_include.json()

        # Matches Immunisation History API in that it doesn't matter if you don't pass "_include".

        # Ignore self link which will always differ.
        result["link"] = []
        result_without_include["link"] = []
        assert result == result_without_include

    def test_search_reject_tbc(self):
        # Given patient has a vaccine with no NHS number
        imms = create_an_imms_obj(str(uuid.uuid4()), "TBC", VaccineTypes.mmr)
        del imms["contained"][1]["identifier"][0]["value"]
        imms["contained"][1]["identifier"][0]["extension"][0]["valueCodeableConcept"]["coding"][0]["code"] = "04"
        self.store_records(imms)

        # When
        # TODO: VACCINE_TYPE Use VaccineTypes enum here
        response = self.default_imms_api.search_immunizations("TBC", "MMR")
        # Then
        self.assert_operation_outcome(response, 400)
