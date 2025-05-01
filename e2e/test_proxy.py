import os
import subprocess
import unittest
import uuid
import requests
from utils.immunisation_api import ImmunisationApi
from lib.env import get_service_base_path, get_status_endpoint_api_key


class TestProxyHealthcheck(unittest.TestCase):

    proxy_url: str
    status_api_key: str

    @classmethod
    def setUpClass(cls):
        cls.proxy_url = get_service_base_path()
        cls.status_api_key = get_status_endpoint_api_key()

    def test_ping(self):
        """/_ping should return 200 if proxy is up and running"""
        response = ImmunisationApi.make_request_with_backoff(
            http_method="GET", url=f"{self.proxy_url}/_ping"
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_status(self):
        """/_status should return 200 if proxy can reach to the backend"""
        response = ImmunisationApi.make_request_with_backoff(
            http_method="GET",
            url=f"{self.proxy_url}/_status",
            headers={"apikey": self.status_api_key},
            is_status_check=True,
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()

        self.assertEqual(
            body["status"].lower(),
            "pass",
            f"service is not healthy: status: {body['status']}",
        )


class TestMtls(unittest.TestCase):
    """Our backend is secured using mTLS. This test makes sure you can't hit the backend directly"""

    def test_mtls(self):
        """backend should reject unauthorized connections"""
        backend_url = TestMtls.get_backend_url()
        backend_health = f"https://{backend_url}/status"

        with self.assertRaises(requests.exceptions.RequestException) as e:
            ImmunisationApi.make_request_with_backoff(
                http_method="GET",
                url=backend_health,
                headers={"X-Request-ID": str(uuid.uuid4())},
            )
            self.assertTrue("RemoteDisconnected" in str(e.exception))

    @staticmethod
    def get_backend_url() -> str:
        """The output is the backend url that terraform has deployed.
        This command runs a make target in the terraform directory only if it's not in env var
        """
        if url := os.getenv("AWS_DOMAIN_NAME"):
            return url

        terraform_path = f"{os.getcwd()}/../terraform"
        "make -C ../terraform -s output name=service_domain_name"
        cmd = ["make", "-C", terraform_path, "-s", "output", "name=service_domain_name"]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
            if res.returncode != 0:
                cmd_str = " ".join(cmd)
                raise RuntimeError(
                    f"Failed to run command: '{cmd_str}'\nDiagnostic: Try to run the same command in the "
                    f"same terminal. Make sure you are authenticated\n{res.stdout}"
                )
            return res.stdout
        except FileNotFoundError:
            raise RuntimeError(
                "Make sure you install terraform. This test can only be run if you have access to the"
                "backend deployment"
            )
        except RuntimeError as e:
            raise RuntimeError(f"Failed to run command\n{e}")


class TestProxyAuthorization(unittest.TestCase):
    """Our apigee proxy has its own authorization.
    This class test different authorization access levels/roles authentication types that are supported
    """

    proxy_url: str

    @classmethod
    def setUpClass(cls):
        cls.proxy_url = get_service_base_path()

    def test_invalid_access_token(self):
        """it should return 401 if access token is invalid"""
        response = ImmunisationApi.make_request_with_backoff(
            http_method="GET",
            url=f"{self.proxy_url}/Immunization",
            headers={"X-Request-ID": str(uuid.uuid4())},
            expected_status_code=401,
        )
        self.assertEqual(response.status_code, 401, response.text)
