"""_summary_

Yields:
    _type_: _description_
"""
from contextlib import contextmanager
import os
import logging
import responses


class MockPds:
    """
    Mock PDS URL for testing purposes.
    This class provides a context manager to mock the PDS URL for testing
    the creation of immunization resources.
    It uses the `responses` library to intercept HTTP requests and return
    predefined responses.
    """
    def __init__(self):
        self.logger = logging.getLogger("MockPds")
        self.logger.basicConfig(level=logging.INFO)
        self.logger.info("MockPds...init")
        env = os.getenv("ENVIRONMENT")
        self.should_mock = env == "internal-dev"
        self.pds_url = f"https://{env}.api.service.nhs.uk/personal-demographics/FHIR/R4/Patient"
        self.logger.info("Should mock: %s, url: %s", self.should_mock, self.pds_url)

    @contextmanager
    def mock_pds_url(self, headers, body, http_method="GET", status=200):
        """
        Set up mocking for the PDS URL only if the environment is set to "internal-dev".
        """
        if self.should_mock:
            self.logger.info("mock_get_patient_details...mock PDS URL")
            responses.add(
                http_method,
                f"{self.pds_url}/123",
                # Use body if supplied, otherwise json
                body=body if body else None,
                json=None if body else {"meta": {"security": [{"code": "U"}]}},
                headers=headers,
                # Set content type only if body is used
                content_type='application/json' if body else None,
                status=status
            )
        try:
            yield  # Allow the test to proceed
        finally:
            responses.reset()  # Clean up after the test
