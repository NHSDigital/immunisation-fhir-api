from contextlib import contextmanager
import logging
import responses


class MockPds:
    def __init__(self, pds_url, should_mock):
        self.logger = logging.getLogger("TestCreateImmunization")
        self.pds_url = pds_url
        self.should_mock = should_mock

    @contextmanager
    def mock_pds_url(self, headers, body):
        if self.should_mock:
            self.logger.info("mock_get_patient_details...mock PDS URL")
            responses.add(
                responses.GET,
                f"{self.pds_url}/123",
                # Use body if supplied, otherwise json
                body=body if body else None,
                json=None if body else {"meta": {"security": [{"code": "U"}]}},
                headers=headers,
                # Set content type only if body is used
                content_type='application/json' if body else None,
                status=200
            )
        try:
            yield  # Allow the test to proceed
        finally:
            responses.reset()  # Clean up after the test

        return None