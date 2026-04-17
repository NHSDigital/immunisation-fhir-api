import json
import unittest
from unittest.mock import Mock, patch

import boto3
import responses
from moto import mock_aws

import common.api_clients.get_pds_details as get_pds_details_module
from lambda_handler import lambda_handler
from process_records import extract_trace_ids, process_record, process_records
from test_utils import generate_private_key_b64, load_sample_sqs_event


class TestExtractTraceIds(unittest.TestCase):
    """Tests for extract_trace_ids helper function."""

    @classmethod
    def setUpClass(cls):
        """Load the sample SQS event once for all tests."""
        cls.sample_sqs_event = load_sample_sqs_event()

    def test_extract_trace_ids_success_from_real_payload(self):
        """Test successful extraction using real SQS event structure."""
        message_id, immunisation_id = extract_trace_ids(self.sample_sqs_event)

        self.assertEqual(message_id, "98ed30eb-829f-41df-8a73-57fef70cf161")
        self.assertEqual(immunisation_id, "d058014c-b0fd-4471-8db9-3316175eb825")

    def test_extract_trace_ids_missing_message_id(self):
        """Test extraction when messageId is missing."""
        record = {"body": json.dumps({"dynamodb": {"NewImage": {"ImmsID": {"S": "imms-456"}}}})}

        message_id, immunisation_id = extract_trace_ids(record)

        self.assertEqual(message_id, "unknown")
        self.assertEqual(immunisation_id, "imms-456")

    def test_extract_trace_ids_missing_body(self):
        """Test extraction when body is missing."""
        record = {"messageId": "msg-123"}

        message_id, immunisation_id = extract_trace_ids(record)

        self.assertEqual(message_id, "msg-123")
        self.assertIsNone(immunisation_id)

    def test_extract_trace_ids_invalid_json_body(self):
        """Test extraction when body contains invalid JSON."""
        record = {"messageId": "msg-123", "body": "not valid json"}

        message_id, immunisation_id = extract_trace_ids(record)

        self.assertEqual(message_id, "msg-123")
        self.assertIsNone(immunisation_id)

    def test_extract_trace_ids_missing_dynamodb_structure(self):
        """Test extraction when DynamoDB structure is incomplete."""
        record = {"messageId": "msg-123", "body": json.dumps({"other": "data"})}

        message_id, immunisation_id = extract_trace_ids(record)

        self.assertEqual(message_id, "msg-123")
        self.assertIsNone(immunisation_id)


class TestProcessRecord(unittest.TestCase):
    """Tests for process_record function."""

    @classmethod
    def setUpClass(cls):
        """Load the sample SQS event once for all tests."""
        cls.sample_sqs_record = load_sample_sqs_event()

    def setUp(self):
        """Set up test fixtures."""
        self.sample_notification = {
            "id": "notif-789",
            "specversion": "1.0",
            "type": "imms-vaccinations-1",
            "filtering": {"action": "CREATE"},
        }
        self.mock_mns_service = Mock()

    @patch("process_records.create_mns_notification")
    @patch("process_records.logger")
    def test_process_record_success(self, mock_logger, mock_create_notification):
        """Test successful processing of a single record."""
        mock_create_notification.return_value = self.sample_notification
        self.mock_mns_service.publish_notification.return_value = None

        process_record(self.sample_sqs_record, self.mock_mns_service)

        mock_create_notification.assert_called_once_with(self.sample_sqs_record)
        self.mock_mns_service.publish_notification.assert_called_once_with(self.sample_notification)
        mock_logger.exception.assert_not_called()

    @patch("process_records.create_mns_notification")
    @patch("process_records.logger")
    def test_process_record_create_notification_failure(self, mock_logger, mock_create_notification):
        """Test handling when notification creation fails."""
        mock_create_notification.side_effect = Exception("Creation error")

        with self.assertRaises(Exception):
            process_record(self.sample_sqs_record, self.mock_mns_service)

        self.mock_mns_service.publish_notification.assert_not_called()

    @patch("process_records.create_mns_notification")
    @patch("process_records.logger")
    def test_process_record_publish_failure(self, mock_logger, mock_create_notification):
        """Test handling when MNS publish fails."""
        mock_create_notification.return_value = self.sample_notification
        self.mock_mns_service.publish_notification.side_effect = Exception("Publish error")

        with self.assertRaises(Exception):
            process_record(self.sample_sqs_record, self.mock_mns_service)


class TestProcessRecords(unittest.TestCase):
    """Tests for process_records function."""

    @classmethod
    def setUpClass(cls):
        """Load the sample SQS event once for all tests."""
        cls.sample_sqs_record = load_sample_sqs_event()

    @patch("process_records.logger")
    @patch("process_records._get_runtime_mns_service")
    @patch("process_records.process_record")
    def test_process_records_all_success(self, mock_process_record, mock_get_mns, mock_logger):
        """Test processing multiple records with all successes."""
        mock_mns_service = Mock()
        mock_get_mns.return_value = mock_mns_service
        mock_process_record.return_value = None

        record_2 = self.sample_sqs_record.copy()
        record_2["messageId"] = "different-id"
        records = [self.sample_sqs_record, record_2]

        result = process_records(records)

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(mock_process_record.call_count, 2)
        mock_get_mns.assert_called_once()
        mock_logger.info.assert_called_with("Successfully processed all 2 messages")

    @patch("process_records.logger")
    @patch("process_records._get_runtime_mns_service")
    @patch("process_records.process_record")
    def test_process_records_partial_failure(self, mock_process_record, mock_get_mns, mock_logger):
        """Test processing with some failures."""
        mock_mns_service = Mock()
        mock_get_mns.return_value = mock_mns_service
        mock_process_record.side_effect = [
            None,
            Exception("Processing error"),
        ]

        record_2 = self.sample_sqs_record.copy()
        record_2["messageId"] = "msg-456"
        records = [self.sample_sqs_record, record_2]

        result = process_records(records)

        self.assertEqual(len(result["batchItemFailures"]), 1)
        self.assertEqual(result["batchItemFailures"][0]["itemIdentifier"], "msg-456")
        mock_logger.warning.assert_called_with("Batch completed with 1 failures")

    @patch("process_records.logger")
    @patch("process_records._get_runtime_mns_service")
    @patch("process_records.process_record")
    def test_process_records_empty_list(self, mock_process_record, mock_get_mns, mock_logger):
        """Test processing empty record list."""
        mock_mns_service = Mock()
        mock_get_mns.return_value = mock_mns_service

        result = process_records([])

        self.assertEqual(result, {"batchItemFailures": []})
        mock_process_record.assert_not_called()
        mock_logger.info.assert_called_with("Successfully processed all 0 messages")

    @patch("process_records.logger")
    @patch("process_records._get_runtime_mns_service")
    @patch("process_records.process_record")
    def test_process_records_mns_service_created_once(self, mock_process_record, mock_get_mns, mock_logger):
        """Test that MNS service is created only once for batch."""
        mock_mns_service = Mock()
        mock_get_mns.return_value = mock_mns_service
        mock_process_record.return_value = None

        records = [self.sample_sqs_record, self.sample_sqs_record, self.sample_sqs_record]

        process_records(records)

        mock_get_mns.assert_called_once()


class TestLambdaHandler(unittest.TestCase):
    """Tests for lambda_handler function."""

    @classmethod
    def setUpClass(cls):
        """Load the sample SQS event once for all tests."""
        cls.sample_sqs_record = load_sample_sqs_event()

    @patch("lambda_handler.process_records")
    def test_lambda_handler_all_success(self, mock_process_records):
        """Test lambda handler with all records succeeding."""
        mock_process_records.return_value = {"batchItemFailures": []}

        event = {"Records": [self.sample_sqs_record]}
        result = lambda_handler(event, Mock())

        self.assertEqual(result, {"batchItemFailures": []})
        mock_process_records.assert_called_once_with([self.sample_sqs_record])

    @patch("lambda_handler.process_records")
    def test_lambda_handler_with_failures(self, mock_process_records):
        """Test lambda handler with some failures."""
        mock_process_records.return_value = {"batchItemFailures": [{"itemIdentifier": "msg-123"}]}

        event = {"Records": [self.sample_sqs_record]}
        result = lambda_handler(event, Mock())

        self.assertEqual(result, {"batchItemFailures": [{"itemIdentifier": "msg-123"}]})

    @patch("lambda_handler.process_records")
    def test_lambda_handler_empty_records(self, mock_process_records):
        """Test lambda handler with no records."""
        mock_process_records.return_value = {"batchItemFailures": []}

        event = {"Records": []}
        result = lambda_handler(event, Mock())

        self.assertEqual(result, {"batchItemFailures": []})
        mock_process_records.assert_called_once_with([])


@mock_aws
class TestLambdaHandlerIntegration(unittest.TestCase):
    """
    Integration tests
    """

    def setUp(self):
        """Set up mocked AWS services and test data."""
        self.sample_sqs_record = load_sample_sqs_event()
        get_pds_details_module._pds_service = None
        self.secrets_client = boto3.client("secretsmanager", region_name="eu-west-2")
        self.secrets_client.create_secret(
            Name="imms/pds/int/jwt-secrets",
            SecretString=json.dumps(
                {"api_key": "fake-pds-api-key", "kid": "fake-kid-123", "private_key_b64": generate_private_key_b64()}
            ),
        )

    def tearDown(self):
        get_pds_details_module._pds_service = None

    @responses.activate
    @patch("common.api_clients.authentication.AppRestrictedAuth.get_access_token")
    @patch("process_records.logger")
    def test_successful_notification_creation_with_gp(self, mock_logger, mock_get_token):
        """
        Test a Successful MNS Publish notification with calls to PDS for GP details, no batch failure
        """

        # Mock OAuth token response issued from Apigee
        mock_get_token.return_value = {"access_token": "fake-token"}

        # Intercepts actual request call to PDS and returns mocked responses
        responses.add(
            responses.GET,
            "https://int.api.service.nhs.uk/personal-demographics/FHIR/R4/Patient/9481152782",
            json={"generalPractitioner": [{"identifier": {"value": "Y12345", "period": {"start": "2024-01-01"}}}]},
            status=200,
        )

        mns_response = responses.add(
            responses.POST,
            "https://int.api.service.nhs.uk/multicast-notification-service/events",
            json={"id": "236a1d4a-5d69-4fa9-9c7f-e72bf505aa5b"},
            status=200,
        )

        sqs_event = {"Records": [self.sample_sqs_record]}
        result = lambda_handler(sqs_event, Mock())
        self.assertEqual(result, {"batchItemFailures": []})

        self.assertEqual(mns_response.call_count, 1)
        self.assertEqual(mns_response.calls[0].response.status_code, 200)
        mns_payload = json.loads(mns_response.calls[0].request.body)
        self.assertEqual(mns_payload["subject"], "9481152782")
        self.assertEqual(mns_payload["filtering"]["generalpractitioner"], "Y12345")
        self.assertEqual(mns_payload["filtering"]["sourceorganisation"], "B0C4P")
        self.assertEqual(mns_payload["filtering"]["sourceapplication"], "TPP")
        self.assertEqual(mns_payload["filtering"]["immunisationtype"], "HIB")
        self.assertEqual(mns_payload["filtering"]["action"], "CREATE")
        self.assertEqual(mns_payload["filtering"]["subjectage"], 21)

        mock_logger.info.assert_any_call("Successfully processed all 1 messages")

    @responses.activate
    @patch("common.api_clients.authentication.AppRestrictedAuth.get_access_token")
    @patch("process_records._get_runtime_mns_service")
    @patch("process_records.logger")
    def test_pds_failure(self, mock_logger, mock_get_mns, mock_get_token):
        """
        Test that a PDS client error results in a batch item failure and MNS is not called.
        """

        # Mock OAuth token response issued from Apigee
        mock_get_token.return_value = "fake-token"

        # Intercepts actual request call to PDS and returns mocked responses
        responses.add(
            responses.GET,
            "https://int.api.service.nhs.uk/personal-demographics/FHIR/R4/Patient/9481152782",
            json={
                "resourceType": "OperationOutcome",
                "issue": [{"severity": "error", "code": "processing", "diagnostics": "Patient not found"}],
            },
            status=400,
        )

        mock_mns_service = Mock()
        mock_mns_service.publish_notification.return_value = None
        mock_get_mns.return_value = mock_mns_service

        sqs_event = {"Records": [self.sample_sqs_record]}
        result = lambda_handler(sqs_event, Mock())

        self.assertEqual(len(result["batchItemFailures"]), 1)
        mock_mns_service.publish_notification.assert_not_called()
        mock_logger.warning.assert_called_with("Batch completed with 1 failures")

    @responses.activate
    @patch("common.api_clients.authentication.AppRestrictedAuth.get_access_token")
    @patch("process_records.logger")
    def test_successful_notification_creation_with_expired_gp(self, mock_logger, mock_get_token):
        """
        Test a Successful MNS Publish notification with calls to PDS for GP details, no batch failure
        """

        # Mock OAuth token response issued from Apigee
        mock_get_token.return_value = {"access_token": "fake-token"}

        # Intercepts actual request call to PDS and returns mocked responses
        responses.add(
            responses.GET,
            "https://int.api.service.nhs.uk/personal-demographics/FHIR/R4/Patient/9481152782",
            json={
                "generalPractitioner": [
                    {"identifier": {"value": "Y12345", "period": {"start": "2024-01-01", "end": "2025-12-31"}}}
                ]
            },
            status=200,
        )

        mns_response = responses.add(
            responses.POST,
            "https://int.api.service.nhs.uk/multicast-notification-service/events",
            json={"id": "236a1d4a-5d69-4fa9-9c7f-e72bf505aa5b"},
            status=200,
        )

        sqs_event = {"Records": [self.sample_sqs_record]}
        result = lambda_handler(sqs_event, Mock())

        self.assertEqual(result, {"batchItemFailures": []})

        self.assertEqual(mns_response.call_count, 1)
        self.assertEqual(mns_response.calls[0].response.status_code, 200)
        mns_payload = json.loads(mns_response.calls[0].request.body)
        self.assertEqual(mns_payload["subject"], "9481152782")
        self.assertEqual(mns_payload["filtering"]["generalpractitioner"], None)
        self.assertEqual(mns_payload["filtering"]["sourceorganisation"], "B0C4P")
        self.assertEqual(mns_payload["filtering"]["sourceapplication"], "TPP")
        self.assertEqual(mns_payload["filtering"]["immunisationtype"], "HIB")
        self.assertEqual(mns_payload["filtering"]["action"], "CREATE")
        self.assertEqual(mns_payload["filtering"]["subjectage"], 21)

        mock_logger.info.assert_any_call("Successfully processed all 1 messages")

    @responses.activate
    @patch.dict("os.environ", {"PDS_BASE_URL": "https://mock-pds.example/Patient"}, clear=False)
    @patch("process_records._get_runtime_mns_service")
    @patch("process_records.logger")
    def test_successful_notification_creation_with_mock_pds_base_url(self, mock_logger, mock_get_mns):
        responses.add(
            responses.GET,
            "https://mock-pds.example/Patient/9481152782",
            json={"generalPractitioner": [{"identifier": {"value": "Y12345", "period": {"start": "2024-01-01"}}}]},
            status=200,
        )

        mock_mns_service = Mock()
        mock_get_mns.return_value = mock_mns_service

        sqs_event = {"Records": [self.sample_sqs_record]}
        result = lambda_handler(sqs_event, Mock())

        self.assertEqual(result, {"batchItemFailures": []})
        mock_mns_service.publish_notification.assert_called_once()
        mns_payload = mock_mns_service.publish_notification.call_args.args[0]
        self.assertEqual(mns_payload["filtering"]["generalpractitioner"], "Y12345")
        mock_logger.info.assert_any_call("Successfully processed all 1 messages")

    @responses.activate
    @patch.dict("os.environ", {"PDS_BASE_URL": "https://mock-pds.example/Patient"}, clear=False)
    @patch("process_records._get_runtime_mns_service")
    @patch("process_records.logger")
    def test_mock_pds_rate_limit_results_in_batch_failure(self, mock_logger, mock_get_mns):
        responses.add(
            responses.GET,
            "https://mock-pds.example/Patient/9481152782",
            json={"code": 429, "message": "Mock PDS rate limit has been exceeded"},
            status=429,
        )

        mock_mns_service = Mock()
        mock_get_mns.return_value = mock_mns_service

        sqs_event = {"Records": [self.sample_sqs_record]}
        result = lambda_handler(sqs_event, Mock())

        self.assertEqual(len(result["batchItemFailures"]), 1)
        mock_mns_service.publish_notification.assert_not_called()
        mock_logger.warning.assert_called_with("Batch completed with 1 failures")
