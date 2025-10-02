"""Generic utils for tests"""

import unittest
from src.models.utils.generic_utils import form_json
from testing_utils.generic_utils import load_json_data, format_date_types

import unittest
from datetime import datetime, date


class TestFormJson(unittest.TestCase):
    def setUp(self):
        self.baseurl = "https://api.service.nhs.uk/immunisation-fhir-api/Immunization"
        self.identifier = "https://supplierABC/identifiers/vacc|f10b59b3-fc73-4616-99c9-9e882ab31184"
        self.response = {
            "resource": load_json_data("completed_covid19_immunization_event.json"),
            "id": "f10b59b3-fc73-4616-99c9-9e882ab31184",
            "version": "2",
        }

        self.maxDiff = None

    def test_no_response(self):
        out = form_json(None, None, self.identifier, self.baseurl)
        self.assertEqual(out["resourceType"], "Bundle")
        self.assertEqual(out["type"], "searchset")
        self.assertEqual(out["link"][0]["url"], f"{self.baseurl}?identifier={self.identifier}")
        self.assertEqual(out["entry"], [])
        self.assertEqual(out["total"], 0)

    def test_identifier_only_returns_full_resource(self):
        out = form_json(self.response, None, self.identifier, self.baseurl)
        self.assertEqual(out["total"], 1)
        self.assertEqual(out["link"][0]["url"], f"{self.baseurl}?identifier={self.identifier}")
        self.assertDictEqual(out["entry"][0]["resource"], self.response["resource"])
        self.assertEqual(out["entry"][0]["fullUrl"], f"{self.baseurl}/{self.response['id']}")

    def test_identifier_with_id_element_truncates_to_id(self):
        out = form_json(self.response, "id", self.identifier, self.baseurl)
        res = out["entry"][0]["resource"]
        self.assertEqual(out["total"], 1)
        self.assertEqual(out["link"][0]["url"], f"{self.baseurl}?identifier={self.identifier}&_elements=id")
        self.assertEqual(res["resourceType"], "Immunization")
        self.assertEqual(res["id"], self.response["id"])
        self.assertNotIn("meta", res)

    def test_identifier_with_meta_element_truncates_to_meta(self):
        out = form_json(self.response, "meta", self.identifier, self.baseurl)
        res = out["entry"][0]["resource"]
        self.assertEqual(out["total"], 1)
        self.assertEqual(out["link"][0]["url"], f"{self.baseurl}?identifier={self.identifier}&_elements=meta")
        self.assertEqual(res["resourceType"], "Immunization")
        self.assertIn("meta", res)
        self.assertEqual(res["meta"]["versionId"], self.response["version"])

    def test_identifier_with_id_and_meta_elements_truncates_both(self):
        out = form_json(self.response, "id,meta", self.identifier, self.baseurl)
        res = out["entry"][0]["resource"]
        self.assertEqual(out["total"], 1)
        self.assertEqual(out["link"][0]["url"], f"{self.baseurl}?identifier={self.identifier}&_elements=id,meta")
        self.assertEqual(res["resourceType"], "Immunization")
        self.assertEqual(res["id"], self.response["id"])
        self.assertIn("meta", res)
        self.assertEqual(res["meta"]["versionId"], self.response["version"])

    def test_elements_whitespace_and_case_are_handled(self):
        raw_elements = "  ID ,  MeTa  "
        out = form_json(self.response, raw_elements, self.identifier, self.baseurl)
        res = out["entry"][0]["resource"]
        self.assertEqual(
            out["link"][0]["url"],
            f"{self.baseurl}?identifier={self.identifier}&_elements={raw_elements}"
        )
        self.assertEqual(res["id"], self.response["id"])
        self.assertEqual(res["meta"]["versionId"], self.response["version"])


class TestFormatFutureDates(unittest.TestCase):
    def test_date_mode_formats_dates_and_datetimes(self):
        inputs = [date(2100, 1, 2), datetime(2100, 1, 3, 12, 0, 0)]
        expected = ["2100-01-02", "2100-01-03"]
        self.assertEqual(format_date_types(inputs, mode="date"), expected)

    def test_datetime_mode_formats_dates_and_datetimes(self):
        inputs = [date(2100, 1, 2), datetime(2100, 1, 3, 12, 0, 0)]
        expected = ["2100-01-02", "2100-01-03T12:00:00"]
        self.assertEqual(format_date_types(inputs, mode="datetime"), expected)

    def test_default_auto_mode_is_currently_unsupported(self):
        # Current implementation raises TypeError when mode is not 'date' or 'datetime'
        inputs = [date(2100, 1, 2)]
        with self.assertRaises(TypeError):
            format_date_types(inputs)  # default mode is 'auto'


if __name__ == "__main__":
    unittest.main()
