import unittest
from time import sleep

import requests

from lib.env import get_service_base_path, get_status_endpoint_api_key, get_source_commit_id

"""Tests in this package don't really test anything. Platform created these tests to check if the current
deployment is the latest. It works by hitting /_status endpoint and comparing the commit sha code of the
deployment with the one that returned from the deployed proxy.
You can ignore these tests if you are running them in your local environment"""


@unittest.skip("This test is skipped because it requires a live FHIR server connection.")
class TestDeployment(unittest.TestCase):
    proxy_url: str
    status_api_key: str
    expected_commit_id: str

    max_retries = 30

    @classmethod
    def setUpClass(cls):
        cls.proxy_url = get_service_base_path()
        cls.status_api_key = get_status_endpoint_api_key()
        cls.expected_commit_id = get_source_commit_id()

    def test_wait_for_ping(self):
        url = f"{self.proxy_url}/_ping"
        self.check_and_retry(url, {}, self.expected_commit_id)

    def test_wait_for_status(self):
        url = f"{self.proxy_url}/_status"
        self.check_and_retry(url, {"apikey": self.status_api_key}, self.expected_commit_id)

    def check_and_retry(self, url, headers, expected_commit_id):
        for i in range(self.max_retries):
            resp = requests.get(url, headers=headers)
            status_code = resp.status_code
            if status_code != 200:
                self.fail(f"Status code {status_code}, expecting 200")

            deployed_commit_id = resp.json().get("commitId")
            if status_code == 200 and deployed_commit_id == expected_commit_id:
                return
            sleep(3)

        self.fail("Timeout Error - max retries")
