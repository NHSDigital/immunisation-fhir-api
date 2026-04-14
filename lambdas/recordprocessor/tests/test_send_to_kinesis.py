import unittest
from unittest.mock import patch

from moto import mock_aws

from tests.utils_for_recordprocessor_tests.mock_environment_variables import (
    MOCK_ENVIRONMENT_DICT,
)
from tests.utils_for_recordprocessor_tests.utils_for_recordprocessor_tests import (
    GenericSetUp,
    GenericTearDown,
    create_boto3_clients,
)

with patch("os.environ", MOCK_ENVIRONMENT_DICT):
    from send_to_kinesis import send_to_kinesis

kinesis_client = None


@mock_aws
class TestSendToKinesis(unittest.TestCase):
    def setUp(self) -> None:
        global kinesis_client
        (kinesis_client,) = create_boto3_clients("kinesis")
        GenericSetUp(None, None, kinesis_client)

    def tearDown(self) -> None:
        GenericTearDown(None, None, kinesis_client)

    @patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
    def test_send_to_kinesis_success(self):
        kinesis_client.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

        # arrange required parameters
        supplier = "test_supplier"
        message_body = {"key": "value"}
        vaccine_type = "test_vaccine"

        result = send_to_kinesis(supplier, message_body, vaccine_type)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
