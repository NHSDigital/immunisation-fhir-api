import unittest

import responses
from immunisation_api import ImmunisationApi
from responses import matchers


class TestImmsApiService(unittest.TestCase):
    def setUp(self):
        self.url = "https://example.com"
        self.imms_api = ImmunisationApi(self.url)

    @responses.activate
    def test_post_event(self):
        act_res = {"response": "OK"}
        payload = {"foo": "bar"}
        exp_header = {
            "Content-Type": "application/fhir+json",
        }
        responses.add(responses.POST, f"{self.url}/event",
                      json=act_res, status=201,
                      match=[matchers.json_params_matcher(payload), matchers.header_matcher(exp_header)])

        resp = self.imms_api.post_event(payload)
        self.assertEqual(resp.json(), act_res)
