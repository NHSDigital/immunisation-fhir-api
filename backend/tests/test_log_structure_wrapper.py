import json
import unittest
from unittest.mock import patch

from log_structure import function_info


@patch("log_structure.firehose_logger")
@patch("log_structure.logger")
class TestFunctionInfoWrapper(unittest.TestCase):
    def setUp(self):
        self.redis_patcher = patch("models.utils.validation_utils.redis_client")
        self.mock_redis_client = self.redis_patcher.start()

    def tearDown(self):
        patch.stopall()

    @staticmethod
    def mock_success_function(_event, _context):
        return "Success"

    @staticmethod
    def mock_function_raises(_event, _context):
        raise ValueError("Test error")

    def extract_all_call_args_for_logger(self, mock_logger) -> list:
        """Extracts all arguments for logger.*."""
        return (
            [args[0] for args, _ in mock_logger.info.call_args_list]
            + [args[0] for args, _ in mock_logger.warning.call_args_list]
            + [args[0] for args, _ in mock_logger.error.call_args_list]
        )

    def test_successful_execution(self, mock_logger, mock_firehose_logger):
        # Arrange
        test_correlation = "test_correlation"
        test_request = "test_request"
        test_supplier = "test_supplier"
        test_actual_path = "/test"
        test_resource_path = "/test"

        self.mock_redis_client.hget.return_value = "FLU"
        wrapped_function = function_info(self.mock_success_function)
        event = {
            "headers": {
                "X-Correlation-ID": test_correlation,
                "X-Request-ID": test_request,
                "SupplierSystem": test_supplier,
            },
            "path": test_actual_path,
            "requestContext": {"resourcePath": test_resource_path},
            "body": '{"identifier": [{"system": "http://test", "value": "12345"}], "protocolApplied": [{"targetDisease": [{"coding": [{"system": "http://snomed.info/sct", "code": "840539006", "display": "Disease caused by severe acute respiratory syndrome coronavirus 2"}]}]}]}',
        }

        # Act
        result = wrapped_function(event, {})

        # Assert
        self.assertEqual(result, "Success")
        mock_logger.info.assert_called()
        mock_firehose_logger.send_log.assert_called()

        args, kwargs = mock_logger.info.call_args
        logged_info = json.loads(args[0])

        self.assertIn("function_name", logged_info)
        self.assertIn("time_taken", logged_info)
        self.assertEqual(logged_info["X-Correlation-ID"], test_correlation)
        self.assertEqual(logged_info["X-Request-ID"], test_request)
        self.assertEqual(logged_info["supplier"], test_supplier)
        self.assertEqual(logged_info["actual_path"], test_actual_path)
        self.assertEqual(logged_info["resource_path"], test_resource_path)
        self.assertEqual(logged_info["local_id"], "12345^http://test")
        self.assertEqual(logged_info["vaccine_type"], "FLU")

    def test_successful_execution_pii(self, mock_logger, mock_firehose_logger):
        """Pass personally identifiable information in an event, and ensure that it is not logged anywhere."""
        # Arrange
        test_correlation = "test_correlation"
        test_request = "test_request"
        test_supplier = "test_supplier"
        test_actual_path = "/test"
        test_resource_path = "/test"

        self.mock_redis_client.hget.return_value = "FLU"
        wrapped_function = function_info(self.mock_success_function)
        event = {
            "headers": {
                "X-Correlation-ID": test_correlation,
                "X-Request-ID": test_request,
                "SupplierSystem": test_supplier,
            },
            "path": test_actual_path,
            "requestContext": {"resourcePath": test_resource_path},
            "body": '{"identifier": [{"system": "http://test", "value": "12345"}], "contained": [{"resourceType": "Patient", "id": "Pat1", "identifier": [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9693632109"}]}], "protocolApplied": [{"targetDisease": [{"coding": [{"system": "http://snomed.info/sct", "code": "840539006", "display": "Disease caused by severe acute respiratory syndrome coronavirus 2"}]}]}]}',
        }

        # Act
        result = wrapped_function(event, {})

        # Assert
        self.assertEqual(result, "Success")

        for logger_info in self.extract_all_call_args_for_logger(mock_logger):
            self.assertNotIn("9693632109", str(logger_info))

    def test_exception_handling(self, mock_logger, mock_firehose_logger):
        # Arrange
        test_correlation = "failed_test_correlation"
        test_request = "failed_test_request"
        test_supplier = "failed_test_supplier"
        test_actual_path = "/failed_test"
        test_resource_path = "/failed_test"

        self.mock_redis_client.hget.return_value = "FLU"

        # Act
        decorated_function_raises = function_info(self.mock_function_raises)

        with self.assertRaises(ValueError):
            # Assert
            event = {
                "headers": {
                    "X-Correlation-ID": test_correlation,
                    "X-Request-ID": test_request,
                    "SupplierSystem": test_supplier,
                },
                "path": test_actual_path,
                "requestContext": {"resourcePath": test_resource_path},
                "body": '{"identifier": [{"system": "http://test", "value": "12345"}], "protocolApplied": [{"targetDisease": [{"coding": [{"system": "http://snomed.info/sct", "code": "840539006", "display": "Disease caused by severe acute respiratory syndrome coronavirus 2"}]}]}]}',
            }

            context = {}
            decorated_function_raises(event, context)

        # Assert
        mock_logger.exception.assert_called()
        mock_firehose_logger.send_log.assert_called()

        args, kwargs = mock_logger.exception.call_args
        logged_info = json.loads(args[0])

        self.assertIn("function_name", logged_info)
        self.assertIn("time_taken", logged_info)
        self.assertEqual(logged_info["X-Correlation-ID"], test_correlation)
        self.assertEqual(logged_info["X-Request-ID"], test_request)
        self.assertEqual(logged_info["supplier"], test_supplier)
        self.assertEqual(logged_info["actual_path"], test_actual_path)
        self.assertEqual(logged_info["resource_path"], test_resource_path)
        self.assertEqual(logged_info["error"], str(ValueError("Test error")))
        self.assertEqual(logged_info["local_id"], "12345^http://test")
        self.assertEqual(logged_info["vaccine_type"], "FLU")

    def test_body_missing(self, mock_logger, mock_firehose_logger):
        # Arrange
        test_correlation = "failed_test_correlation_body_missing"
        test_request = "failed_test_request_body_missing"
        test_supplier = "failed_test_supplier_body_missing"
        test_actual_path = "/failed_test_body_missing"
        test_resource_path = "/failed_test_body_missing"

        wrapped_function = function_info(self.mock_success_function)
        event = {
            "headers": {
                "X-Correlation-ID": test_correlation,
                "X-Request-ID": test_request,
                "SupplierSystem": test_supplier,
            },
            "path": test_actual_path,
            "requestContext": {"resourcePath": test_resource_path},
        }

        # Act
        wrapped_function(event, {})

        # Assert
        args, kwargs = mock_logger.info.call_args
        logged_info = json.loads(args[0])

        self.assertEqual(logged_info["X-Correlation-ID"], test_correlation)
        self.assertEqual(logged_info["X-Request-ID"], test_request)
        self.assertEqual(logged_info["supplier"], test_supplier)
        self.assertEqual(logged_info["actual_path"], test_actual_path)
        self.assertEqual(logged_info["resource_path"], test_resource_path)
        self.assertNotIn("local_id", logged_info)
        self.assertNotIn("vaccine_type", logged_info)

    def test_body_not_json(self, mock_logger, mock_firehose_logger):
        # Arrange
        test_correlation = "failed_test_correlation_body_not_json"
        test_request = "failed_test_request_body_not_json"
        test_supplier = "failed_test_supplier_body_not_json"
        test_actual_path = "/failed_test_body_not_json"
        test_resource_path = "/failed_test_body_not_json"

        # Act
        decorated_function_raises = function_info(self.mock_function_raises)

        with self.assertRaises(ValueError):
            # Assert
            event = {
                "headers": {
                    "X-Correlation-ID": test_correlation,
                    "X-Request-ID": test_request,
                    "SupplierSystem": test_supplier,
                },
                "path": test_actual_path,
                "requestContext": {"resourcePath": test_resource_path},
                "body": "invalid",
            }

            context = {}
            decorated_function_raises(event, context)

        # Assert
        args, kwargs = mock_logger.exception.call_args
        logged_info = json.loads(args[0])

        self.assertEqual(logged_info["X-Correlation-ID"], test_correlation)
        self.assertEqual(logged_info["X-Request-ID"], test_request)
        self.assertEqual(logged_info["supplier"], test_supplier)
        self.assertEqual(logged_info["actual_path"], test_actual_path)
        self.assertEqual(logged_info["resource_path"], test_resource_path)
        self.assertNotIn("local_id", logged_info)
        self.assertNotIn("vaccine_type", logged_info)

    def test_body_invalid_identifier(self, mock_logger, mock_firehose_logger):
        # Arrange
        test_correlation = "failed_test_correlation_invalid_identifier"
        test_request = "failed_test_request_invalid_identifier"
        test_supplier = "failed_test_supplier_invalid_identifier"
        test_actual_path = "/failed_test_invalid_identifier"
        test_resource_path = "/failed_test_invalid_identifier"

        self.mock_redis_client.hget.return_value = "FLU"

        # Act
        decorated_function_raises = function_info(self.mock_function_raises)

        with self.assertRaises(ValueError):
            # Assert
            event = {
                "headers": {
                    "X-Correlation-ID": test_correlation,
                    "X-Request-ID": test_request,
                    "SupplierSystem": test_supplier,
                },
                "path": test_actual_path,
                "requestContext": {"resourcePath": test_resource_path},
                "body": '{"identifier": [], "protocolApplied": [{"targetDisease": [{"coding": [{"system": "http://snomed.info/sct", "code": "840539006", "display": "Disease caused by severe acute respiratory syndrome coronavirus 2"}]}]}]}',
            }

            context = {}
            decorated_function_raises(event, context)

        # Assert
        args, kwargs = mock_logger.exception.call_args
        logged_info = json.loads(args[0])

        self.assertEqual(logged_info["X-Correlation-ID"], test_correlation)
        self.assertEqual(logged_info["X-Request-ID"], test_request)
        self.assertEqual(logged_info["supplier"], test_supplier)
        self.assertEqual(logged_info["actual_path"], test_actual_path)
        self.assertEqual(logged_info["resource_path"], test_resource_path)
        self.assertNotIn("local_id", logged_info)
        self.assertEqual(logged_info["vaccine_type"], "FLU")

    def test_body_invalid_protocol_applied(self, mock_logger, mock_firehose_logger):
        # Arrange
        test_correlation = "failed_test_correlation_invalid_protocol"
        test_request = "failed_test_request_invalid_protocol"
        test_supplier = "failed_test_supplier_invalid_protocol"
        test_actual_path = "/failed_test_invalid_protocol"
        test_resource_path = "/failed_test_invalid_protocol"

        self.mock_redis_client.hget.return_value = "FLU"

        # Act
        decorated_function_raises = function_info(self.mock_function_raises)

        with self.assertRaises(ValueError):
            # Assert
            event = {
                "headers": {
                    "X-Correlation-ID": test_correlation,
                    "X-Request-ID": test_request,
                    "SupplierSystem": test_supplier,
                },
                "path": test_actual_path,
                "requestContext": {"resourcePath": test_resource_path},
                "body": '{"identifier": [{"system": "http://test", "value": "12345"}], "protocolApplied": []}',
            }

            context = {}
            decorated_function_raises(event, context)

        # Assert
        args, kwargs = mock_logger.exception.call_args
        logged_info = json.loads(args[0])

        self.assertEqual(logged_info["X-Correlation-ID"], test_correlation)
        self.assertEqual(logged_info["X-Request-ID"], test_request)
        self.assertEqual(logged_info["supplier"], test_supplier)
        self.assertEqual(logged_info["actual_path"], test_actual_path)
        self.assertEqual(logged_info["resource_path"], test_resource_path)
        self.assertEqual(logged_info["local_id"], "12345^http://test")
        self.assertNotIn("vaccine_type", logged_info)
