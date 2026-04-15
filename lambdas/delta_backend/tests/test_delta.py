import decimal
import json
import os
import time
import unittest
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

TEST_DEAD_LETTER_QUEUE_URL = "https://sqs.eu-west-2.amazonaws.com/123456789012/test-queue"

os.environ["AWS_SQS_QUEUE_URL"] = TEST_DEAD_LETTER_QUEUE_URL
os.environ["DELTA_TABLE_NAME"] = "my_delta_table"
os.environ["DELTA_TTL_DAYS"] = "14"
os.environ["SOURCE"] = "my_source"

import delta  # noqa: E402 — must come after env vars are set
from delta import (  # noqa: E402
    _event_to_operation,
    _extract_value,
    _normalize_record,
    get_creation_and_expiry_times,
    get_imms_id,
    get_vaccine_type,
    handler,
    process_record,
)
from mappings import ActionFlag, EventName, Operation  # noqa: E402
from utils_for_converter_tests import RecordConfig, ValuesForTests, make_mock_logger  # noqa: E402

SUCCESS_RESPONSE = {"ResponseMetadata": {"HTTPStatusCode": 200}}
DUPLICATE_RESPONSE = ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
EXCEPTION_RESPONSE = ClientError({"Error": {"Code": "InternalServerError"}}, "PutItem")
FAIL_RESPONSE = {"ResponseMetadata": {"HTTPStatusCode": 500}}

_DEFAULT_SEQUENCE = "49590338322303844748686548458181664417"


def _make_stream_record(
    *,
    event_name: str = "INSERT",
    operation: str | None = Operation.CREATE,
    patient_sk: str | None = None,
    sequence_number: str | None = _DEFAULT_SEQUENCE,
    imms: str = '{"foo": 1.23}',
    imms_id: str = "test-imms-id",
    supplier: str | None = None,
) -> dict:
    pk_value = f"Immunization#{imms_id}"
    is_remove = event_name == EventName.DELETE_PHYSICAL  # "REMOVE"

    if is_remove:
        # REMOVE events have no NewImage — PK lives in Keys only
        dynamodb_envelope: dict = {
            "Keys": {
                "PK": {"S": pk_value},
                "PatientSK": {"S": patient_sk or "covid#test-patient-sk"},
            },
        }
        if supplier is not None:
            dynamodb_envelope["Keys"]["SupplierSystem"] = {"S": supplier}
    else:
        new_image: dict = {
            "PK": {"S": pk_value},
            "Imms": {"S": imms},
            "PatientSK": {"S": patient_sk or "covid#test-patient-sk"},
        }
        if operation is not None:
            new_image["Operation"] = {"S": operation}
        if supplier is not None:
            new_image["SupplierSystem"] = {"S": supplier}
        dynamodb_envelope = {"NewImage": new_image}

    if sequence_number is not None:
        dynamodb_envelope["SequenceNumber"] = sequence_number

    return {
        "eventID": f"evt-{int(time.time() * 1000)}",
        "eventName": event_name,
        "dynamodb": dynamodb_envelope,
    }


def _deep_update(base: dict, overrides: dict) -> dict:
    """Recursively merge overrides into base (used in TestNormalizeRecord)."""
    for key, val in overrides.items():
        if isinstance(val, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], val)
        else:
            base[key] = val
    return base


class TestExtractValue(unittest.TestCase):
    """Direct unit tests for _extract_value — catches regressions in DDB marshalling."""

    def test_single_key_dict_unwraps(self):
        self.assertEqual(_extract_value({"S": "hello"}), "hello")

    def test_single_key_dict_numeric(self):
        self.assertEqual(_extract_value({"N": "42"}), "42")

    def test_multi_key_dict_returned_as_is(self):
        val = {"S": "a", "N": "1"}
        self.assertIs(_extract_value(val), val)

    def test_string_returned_as_is(self):
        self.assertEqual(_extract_value("plain"), "plain")

    def test_none_returned_as_is(self):
        self.assertIsNone(_extract_value(None))

    def test_integer_returned_as_is(self):
        self.assertEqual(_extract_value(99), 99)

    def test_empty_dict_returned_as_is(self):
        self.assertEqual(_extract_value({}), {})


class TestGetImmsId(unittest.TestCase):
    def test_standard_pk(self):
        self.assertEqual(get_imms_id("Immunization#abc-123"), "abc-123")

    def test_no_hash_returns_unknown(self):
        self.assertEqual(get_imms_id("badvalue"), "unknown")

    def test_none_returns_unknown(self):
        self.assertEqual(get_imms_id(None), "unknown")

    def test_empty_string_returns_unknown(self):
        self.assertEqual(get_imms_id(""), "unknown")

    def test_multiple_hashes_returns_second_segment(self):
        # Only the first split is used
        self.assertEqual(get_imms_id("Immunization#abc#extra"), "abc")


class TestGetVaccineType(unittest.TestCase):
    def test_standard_patient_sk(self):
        self.assertEqual(get_vaccine_type("covid#patient-1"), "covid")

    def test_whitespace_is_stripped(self):
        self.assertEqual(get_vaccine_type("  flu #patient-1"), "flu")

    def test_lowercase_normalisation(self):
        self.assertEqual(get_vaccine_type("COVID#patient-1"), "covid")

    def test_none_returns_unknown(self):
        self.assertEqual(get_vaccine_type(None), "unknown")

    def test_empty_string_returns_unknown(self):
        self.assertEqual(get_vaccine_type(""), "unknown")


class TestEventToOperation(unittest.TestCase):
    """
    _event_to_operation is error-path only
    """

    def test_insert_maps_to_create(self):
        self.assertEqual(_event_to_operation("INSERT"), Operation.CREATE)

    def test_remove_maps_to_delete_physical(self):
        # EventName.DELETE_PHYSICAL == "REMOVE"
        self.assertEqual(_event_to_operation(EventName.DELETE_PHYSICAL), Operation.DELETE_PHYSICAL)
        self.assertEqual(_event_to_operation("REMOVE"), Operation.DELETE_PHYSICAL)

    def test_modify_maps_to_update_as_best_effort(self):
        # Acceptable ambiguity on error path only
        self.assertEqual(_event_to_operation("MODIFY"), Operation.UPDATE)

    def test_unknown_event_falls_back_to_update(self):
        self.assertEqual(_event_to_operation("UNKNOWN_EVENT"), Operation.UPDATE)


class TestNormalizeRecord(unittest.TestCase):
    def _make_raw(self, **overrides) -> dict:
        base = _make_stream_record(
            event_name="INSERT",
            operation=Operation.CREATE,
            patient_sk="covid#patient-1",
            sequence_number=_DEFAULT_SEQUENCE,
            imms='{"foo": 1}',
            imms_id="imms-abc",
        )
        _deep_update(base, overrides)
        return base

    def test_sequence_number_from_envelope(self):
        norm = _normalize_record(self._make_raw())
        self.assertEqual(norm.sequence_number, _DEFAULT_SEQUENCE)

    def test_primary_key_from_new_image_pk(self):
        norm = _normalize_record(self._make_raw())
        self.assertEqual(norm.primary_key, "Immunization#imms-abc")

    def test_imms_id_derived_from_primary_key(self):
        norm = _normalize_record(self._make_raw())
        self.assertEqual(norm.imms_id, "imms-abc")

    def test_patient_sort_key_from_new_image(self):
        norm = _normalize_record(self._make_raw())
        self.assertEqual(norm.patient_sort_key, "covid#patient-1")

    def test_patient_sort_key_absent_gives_none_and_unknown_vaccine_type(self):
        record = self._make_raw()
        del record["dynamodb"]["NewImage"]["PatientSK"]
        norm = _normalize_record(record)
        self.assertIsNone(norm.patient_sort_key)
        self.assertEqual(norm.vaccine_type, "unknown")

    def test_operation_from_new_image(self):
        norm = _normalize_record(self._make_raw())
        self.assertEqual(norm.operation, Operation.CREATE)

    def test_operation_absent_is_none(self):
        norm = _normalize_record(_make_stream_record(operation=None))
        self.assertIsNone(norm.operation)

    def test_supplier_system_from_new_image(self):
        norm = _normalize_record(_make_stream_record(supplier="RAVS"))
        self.assertEqual(norm.supplier_system, "RAVS")

    def test_supplier_system_absent_is_none(self):
        norm = _normalize_record(self._make_raw())
        self.assertIsNone(norm.supplier_system)

    def test_approximate_creation_datetime_used_when_present(self):
        record = self._make_raw()
        record["dynamodb"]["ApproximateCreationDateTime"] = 1708264245.0
        norm = _normalize_record(record)
        self.assertEqual(norm.creation_timestamp, 1708264245.0)

    @patch("delta.time.time", return_value=9999999.0)
    def test_approximate_creation_datetime_absent_falls_back_to_now(self, _):
        record = self._make_raw()
        record["dynamodb"].pop("ApproximateCreationDateTime", None)
        self.assertEqual(_normalize_record(record).creation_timestamp, 9999999.0)

    def test_resource_field_preferred_over_imms(self):
        record = self._make_raw()
        record["dynamodb"]["NewImage"]["Resource"] = {"S": '{"resourceType": "Immunization"}'}
        self.assertEqual(_normalize_record(record).imms_raw, '{"resourceType": "Immunization"}')

    def test_imms_string_used_when_resource_absent(self):
        self.assertEqual(_normalize_record(self._make_raw()).imms_raw, '{"foo": 1}')

    def test_both_resource_and_imms_absent_gives_none(self):
        record = self._make_raw()
        del record["dynamodb"]["NewImage"]["Imms"]
        self.assertIsNone(_normalize_record(record).imms_raw)

    def test_resource_field_from_real_dynamodb_stream_shape(self):
        record = {
            "eventID": "1",
            "eventName": "INSERT",
            "eventSource": "aws:dynamodb",
            "awsRegion": "eu-west-2",
            "dynamodb": {
                "ApproximateCreationDateTime": 1708264245.0,
                "SequenceNumber": _DEFAULT_SEQUENCE,
                "Keys": {"PK": {"S": "Immunization#imms-abc"}},
                "NewImage": {
                    "PK": {"S": "Immunization#imms-abc"},
                    "PatientSK": {"S": "covid#patient-1"},
                    "Operation": {"S": Operation.CREATE},
                    "SupplierSystem": {"S": "RAVS"},
                    "Resource": {"S": '{"resourceType":"Immunization"}'},
                    "Imms": {"S": '{"foo":1}'},
                },
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
        }
        self.assertEqual(_normalize_record(record).imms_raw, '{"resourceType":"Immunization"}')

    def test_imms_fallback_from_real_dynamodb_stream_shape(self):
        record = {
            "eventID": "2",
            "eventName": "INSERT",
            "eventSource": "aws:dynamodb",
            "awsRegion": "eu-west-2",
            "dynamodb": {
                "ApproximateCreationDateTime": 1708264245.0,
                "SequenceNumber": _DEFAULT_SEQUENCE,
                "Keys": {"PK": {"S": "Immunization#imms-abc"}},
                "NewImage": {
                    "PK": {"S": "Immunization#imms-abc"},
                    "PatientSK": {"S": "covid#patient-1"},
                    "Operation": {"S": Operation.CREATE},
                    "SupplierSystem": {"S": "RAVS"},
                    "Imms": {"S": '{"foo":1}'},
                },
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
        }
        self.assertEqual(_normalize_record(record).imms_raw, '{"foo":1}')


class DeltaHandlerTestCase(unittest.TestCase):
    # TODO refactor for dependency injection, eg process_record, send_firehose etc
    def setUp(self):
        self.logger_patcher = patch("delta.logger", make_mock_logger())
        self.mock_logger = self.logger_patcher.start()

        self.mock_delta_table = MagicMock()
        self.mock_sqs_client = MagicMock()

        self.get_delta_table_patcher = patch("delta.get_delta_table", return_value=self.mock_delta_table)
        self.get_delta_table_patcher.start()

        self.send_log_to_firehose_patcher = patch("delta.send_log_to_firehose")
        self.mock_send_log_to_firehose = self.send_log_to_firehose_patcher.start()

        self.sqs_client_patcher = patch("delta.get_sqs_client", return_value=self.mock_sqs_client)
        self.sqs_client_patcher.start()

    def tearDown(self):
        patch.stopall()

    def _call_process_record(self, record):
        return process_record(
            record,
            self.mock_delta_table,
        )

    def test_handler_success_insert(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        suppliers = ["RAVS", "EMIS"]
        for supplier in suppliers:
            imms_id = f"test-insert-imms-{supplier}-id"
            event = ValuesForTests.get_event(
                event_name=EventName.CREATE,
                operation=Operation.CREATE,
                imms_id=imms_id,
                supplier=supplier,
            )

            # Act
            result = handler(event, None)

            # Assert
            self.assertTrue(result)
            self.mock_delta_table.put_item.assert_called()
            self.mock_send_log_to_firehose.assert_called()  # check logged
            put_item_call_args = self.mock_delta_table.put_item.call_args  # check data written to DynamoDB
            put_item_data = put_item_call_args.kwargs["Item"]
            self.assertIn("Imms", put_item_data)
            self.assertEqual(put_item_data["Imms"]["ACTION_FLAG"], ActionFlag.CREATE)
            self.assertEqual(put_item_data["Operation"], Operation.CREATE)
            self.assertEqual(put_item_data["SupplierSystem"], supplier)
            self.mock_sqs_client.send_message.assert_not_called()

    @patch("delta.process_record")
    def test_partial_success_contract_and_dlq_routing(self, mock_process_record):
        event = {"Records": [{"id": "r1"}, {"id": "r2"}, {"id": "r3"}]}

        partial_msg = "Partial success: successfully synced into delta, but issues found within record"
        mock_process_record.side_effect = [
            (
                True,
                {
                    "record": "id1",
                    "operation_type": Operation.CREATE,
                    "statusCode": "200",
                    "statusDesc": "Successfully synched into delta",
                },
            ),
            (
                True,
                {"record": "id2", "operation_type": Operation.UPDATE, "statusCode": "207", "statusDesc": partial_msg},
            ),
            (
                False,
                {"record": "id3", "operation_type": Operation.UPDATE, "statusCode": "500", "statusDesc": "Exception"},
            ),
        ]

        response = handler(event, None)

        self.assertTrue(response)
        self.assertEqual(self.mock_send_log_to_firehose.call_count, 3)
        self.assertEqual(self.mock_sqs_client.send_message.call_count, 1)

        sent_payloads = [c.args[1] for c in self.mock_send_log_to_firehose.call_args_list]
        self.assertTrue(any(p["operation_outcome"]["statusDesc"] == partial_msg for p in sent_payloads))

    def test_handler_exception(self):
        """Ensure that sqs_client exceptions do not cause the lambda handler itself to raise an exception"""
        # Arrange
        self.mock_sqs_client.send_message.side_effect = Exception("SQS error")
        self.mock_delta_table.put_item.return_value = FAIL_RESPONSE
        event = ValuesForTests.get_event()

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.mock_logger.exception.assert_any_call("Error sending record to DLQ")

    def test_handler_raises_exception_if_called_with_unexpected_event(self):
        """Tests that when the Lambda is invoked with an unexpected event format i.e. no "Records" key, then an
        exception will be raised. The DDB Stream configuration will then ensure that the event is forwarded to the DLQ.
        Note: this would only ever happen if we misconfigured the Lambda or tested manually with a bad event."""
        # Arrange
        event = {"invalid_format": True}

        # Act
        with self.assertRaises(KeyError):
            handler(event, None)

        # Assert
        self.mock_sqs_client.send_message.assert_not_called()

    def test_handler_processing_failure(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = FAIL_RESPONSE
        event = ValuesForTests.get_event()

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.mock_sqs_client.send_message.assert_called_with(
            QueueUrl=TEST_DEAD_LETTER_QUEUE_URL, MessageBody=json.dumps(event["Records"][0])
        )

    def test_handler_success_update(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        imms_id = "test-update-imms-id"
        event = ValuesForTests.get_event(event_name=EventName.UPDATE, operation=Operation.UPDATE, imms_id=imms_id)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.mock_delta_table.put_item.assert_called()
        self.mock_send_log_to_firehose.assert_called()  # check logged
        put_item_call_args = self.mock_delta_table.put_item.call_args  # check data written to DynamoDB
        put_item_data = put_item_call_args.kwargs["Item"]
        self.assertIn("Imms", put_item_data)
        self.assertEqual(put_item_data["Imms"]["ACTION_FLAG"], ActionFlag.UPDATE)
        self.assertEqual(put_item_data["Operation"], Operation.UPDATE)
        self.assertEqual(put_item_data["ImmsID"], imms_id)
        self.mock_sqs_client.send_message.assert_not_called()

    def test_handler_success_delete_physical(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        imms_id = "test-update-imms-id"
        event = ValuesForTests.get_event(
            event_name=EventName.DELETE_PHYSICAL,
            operation=Operation.DELETE_PHYSICAL,
            imms_id=imms_id,
        )

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.mock_delta_table.put_item.assert_called()
        self.mock_send_log_to_firehose.assert_called()  # check logged
        put_item_call_args = self.mock_delta_table.put_item.call_args  # check data written to DynamoDB
        put_item_data = put_item_call_args.kwargs["Item"]
        self.assertIn("Imms", put_item_data)
        self.assertEqual(put_item_data["Operation"], Operation.DELETE_PHYSICAL)
        self.assertEqual(put_item_data["Imms"], "")  # check imms has been blanked out
        self.mock_sqs_client.send_message.assert_not_called()

    def test_handler_success_delete_logical(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        imms_id = "test-update-imms-id"
        event = ValuesForTests.get_event(
            event_name=EventName.UPDATE,
            operation=Operation.DELETE_LOGICAL,
            imms_id=imms_id,
        )
        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.mock_delta_table.put_item.assert_called()
        self.mock_send_log_to_firehose.assert_called()  # check logged
        put_item_call_args = self.mock_delta_table.put_item.call_args  # check data written to DynamoDB
        put_item_data = put_item_call_args.kwargs["Item"]
        self.assertIn("Imms", put_item_data)
        self.assertEqual(put_item_data["Imms"]["ACTION_FLAG"], ActionFlag.DELETE_LOGICAL)
        self.assertEqual(put_item_data["Operation"], Operation.DELETE_LOGICAL)
        self.assertEqual(put_item_data["ImmsID"], imms_id)
        self.mock_sqs_client.send_message.assert_not_called()

    @patch("delta.logger.info")
    def test_dps_record_skipped(self, mock_logger_info):
        event = ValuesForTests.get_event(supplier="DPSFULL")

        response = handler(event, None)

        self.assertTrue(response)

        # Check logging and Firehose were called
        mock_logger_info.assert_any_call("Record from DPS skipped")
        self.mock_send_log_to_firehose.assert_called()
        self.mock_sqs_client.send_message.assert_not_called()

    @patch("delta.Converter")
    def test_partial_success_with_errors(self, mock_converter):
        mock_converter_instance = MagicMock()
        mock_converter_instance.run_conversion.return_value = {"ABC": "DEF"}
        mock_converter_instance.get_error_records.return_value = [{"error": "Invalid field"}]
        mock_converter.return_value = mock_converter_instance

        # Mock DynamoDB put_item success
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE

        event = ValuesForTests.get_event()

        response = handler(event, None)

        self.assertTrue(response)
        # Check logging and Firehose were called
        self.mock_logger.info.assert_called()
        self.assertEqual(self.mock_send_log_to_firehose.call_count, 1)
        self.mock_send_log_to_firehose.assert_called_once()

        # Get the actual argument passed to send_log_to_firehose
        args, kwargs = self.mock_send_log_to_firehose.call_args
        sent_payload = args[1]  # Second positional arg

        # Navigate to the specific message
        status_desc = sent_payload["operation_outcome"]["statusDesc"]

        # Assert the expected message is present
        self.assertIn(
            "Partial success: successfully synced into delta, but issues found within record",
            status_desc,
        )

    def test_send_message_multi_records_diverse(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "id1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "id2", ActionFlag.UPDATE),
            RecordConfig(
                EventName.DELETE_LOGICAL,
                Operation.DELETE_LOGICAL,
                "id3",
                ActionFlag.DELETE_LOGICAL,
            ),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "id4"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, len(records_config))
        self.assertEqual(self.mock_send_log_to_firehose.call_count, len(records_config))

    def test_send_message_skipped_records_diverse(self):
        """Check skipped records sent to firehose but not to DynamoDB"""
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "id1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "id2", ActionFlag.UPDATE),
            RecordConfig(
                EventName.CREATE,
                Operation.CREATE,
                "id-skip",
                ActionFlag.CREATE,
                "DPSFULL",
            ),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "id4"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_send_log_to_firehose.call_count, len(records_config))

    def test_send_message_multi_create(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "create-id1", ActionFlag.CREATE),
            RecordConfig(EventName.CREATE, Operation.CREATE, "create-id2", ActionFlag.CREATE),
            RecordConfig(EventName.CREATE, Operation.CREATE, "create-id3", ActionFlag.CREATE),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_send_log_to_firehose.call_count, 3)

    def test_send_message_multi_update(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        records_config = [
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "update-id1", ActionFlag.UPDATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "update-id2", ActionFlag.UPDATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "update-id3", ActionFlag.UPDATE),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_send_log_to_firehose.call_count, 3)

    def test_send_message_multi_logical_delete(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE

        records_config = [
            RecordConfig(
                EventName.DELETE_LOGICAL,
                Operation.DELETE_LOGICAL,
                "delete-id1",
                ActionFlag.DELETE_LOGICAL,
            ),
            RecordConfig(
                EventName.DELETE_LOGICAL,
                Operation.DELETE_LOGICAL,
                "delete-id2",
                ActionFlag.DELETE_LOGICAL,
            ),
            RecordConfig(
                EventName.DELETE_LOGICAL,
                Operation.DELETE_LOGICAL,
                "delete-id3",
                ActionFlag.DELETE_LOGICAL,
            ),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_send_log_to_firehose.call_count, 3)

    def test_send_message_multi_physical_delete(self):
        # Arrange
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        records_config = [
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "remove-id1"),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "remove-id2"),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "remove-id3"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_send_log_to_firehose.call_count, 3)

    def test_single_error_in_multi(self):
        # Arrange
        self.mock_delta_table.put_item.side_effect = [
            SUCCESS_RESPONSE,
            FAIL_RESPONSE,
            SUCCESS_RESPONSE,
        ]

        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "ok-id1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "fail-id1.2", ActionFlag.UPDATE),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "ok-id1.3"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertEqual(self.mock_send_log_to_firehose.call_count, 3)
        self.assertEqual(self.mock_logger.error.call_count, 1)
        self.assertEqual(self.mock_sqs_client.send_message.call_count, 1)

    def test_single_exception_in_multi(self):
        # Arrange
        # 2nd record fails
        self.mock_delta_table.put_item.side_effect = [
            SUCCESS_RESPONSE,
            EXCEPTION_RESPONSE,
            SUCCESS_RESPONSE,
        ]

        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "ok-id2.1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "exception-id2.2", ActionFlag.UPDATE),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "ok-id2.3"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_sqs_client.send_message.call_count, 1)
        self.assertEqual(self.mock_delta_table.put_item.call_count, len(records_config))
        self.assertEqual(self.mock_send_log_to_firehose.call_count, len(records_config))

    def test_single_duplicate_in_multi(self):
        # Arrange
        self.mock_delta_table.put_item.side_effect = [
            SUCCESS_RESPONSE,
            DUPLICATE_RESPONSE,
            SUCCESS_RESPONSE,
        ]

        records_config = [
            RecordConfig(EventName.CREATE, Operation.CREATE, "ok-id2.1", ActionFlag.CREATE),
            RecordConfig(EventName.UPDATE, Operation.UPDATE, "duplicate-id2.2", ActionFlag.UPDATE),
            RecordConfig(EventName.DELETE_PHYSICAL, Operation.DELETE_PHYSICAL, "ok-id2.3"),
        ]
        event = ValuesForTests.get_multi_record_event(records_config)

        # Act
        result = handler(event, None)

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.mock_delta_table.put_item.call_count, len(records_config))
        self.assertEqual(self.mock_send_log_to_firehose.call_count, len(records_config))

    @patch("delta.process_record")
    @patch("delta.send_log_to_firehose")
    def test_handler_calls_process_record_for_each_event(self, mock_send_log_to_firehose, mock_process_record):
        # Arrange
        event = {"Records": [{"a": "record1"}, {"a": "record2"}, {"a": "record3"}]}
        # Mock process_record to always return True
        mock_process_record.return_value = True, {}
        mock_send_log_to_firehose.return_value = None

        # Act
        result = handler(event, {})

        # Assert
        self.assertTrue(result)
        self.assertEqual(mock_process_record.call_count, len(event["Records"]))

    @patch("delta.process_record")
    @patch("delta.send_log_to_firehose")
    def test_handler_sends_all_to_firehose(self, mock_send_log_to_firehose, mock_process_record):
        # event with 3 records
        event = {"Records": [{"a": "record1"}, {"a": "record2"}, {"a": "record3"}]}
        return_ok = (True, {})
        return_fail = (False, {})
        mock_send_log_to_firehose.return_value = None
        mock_process_record.side_effect = [return_ok, return_fail, return_ok]

        # Act
        result = handler(event, {})

        # Assert
        self.assertTrue(result)
        self.assertEqual(mock_process_record.call_count, len(event["Records"]))
        # check that all records were sent to firehose
        self.assertEqual(mock_send_log_to_firehose.call_count, len(event["Records"]))
        # Only send the failed record to SQS DLQ
        self.assertEqual(self.mock_sqs_client.send_message.call_count, 1)

    def _get_put_item_payload(self) -> dict:
        """Helper: return the Item dict from the most recent put_item call."""
        return self.mock_delta_table.put_item.call_args.kwargs["Item"]

    def _assert_timestamp_fields(self, item: dict) -> None:
        """
        Asserts:
        - DateTimeStamp is present
        - SequenceNumber is present
        - SequenceNumber is consistent
        """
        self.assertIn("DateTimeStamp", item, "DateTimeStamp missing — breaks DPS backward compat (SearchIndex GSI)")
        self.assertIn(
            "SequenceNumber",
            item,
            "SequenceNumber missing — breaks OperationSequenceIndex GSI tie-break range key",
        )
        self.assertNotIn(
            "DateTimeStampWithSequence",
            item,
            "DateTimeStampWithSequence must NOT be present — it has been retired in favour of "
            "native multi-attribute key_schema in OperationSequenceIndex (provider >= 6.33.0)",
        )
        dt: str = item["DateTimeStamp"]
        self.assertGreater(len(dt), 0, "DateTimeStamp must not be empty")

        self.assertIsInstance(item["SequenceNumber"], str, "SequenceNumber must be a string")

    def test_create_put_item_has_correct_timestamp_fields(self):
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        event = ValuesForTests.get_event(event_name=EventName.CREATE, operation=Operation.CREATE, imms_id="ts-create")
        handler(event, None)

        item = self._get_put_item_payload()
        self._assert_timestamp_fields(item)
        self.assertEqual(item["Operation"], Operation.CREATE)

    def test_update_put_item_has_correct_timestamp_fields(self):
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        event = ValuesForTests.get_event(event_name=EventName.UPDATE, operation=Operation.UPDATE, imms_id="ts-update")
        handler(event, None)

        item = self._get_put_item_payload()
        self._assert_timestamp_fields(item)
        self.assertEqual(item["Operation"], Operation.UPDATE)

    def test_delete_logical_put_item_has_correct_timestamp_fields(self):
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        event = ValuesForTests.get_event(
            event_name=EventName.UPDATE, operation=Operation.DELETE_LOGICAL, imms_id="ts-del-logical"
        )
        handler(event, None)

        item = self._get_put_item_payload()
        self._assert_timestamp_fields(item)
        self.assertEqual(item["Operation"], Operation.DELETE_LOGICAL)
        # DELETE_LOGICAL retains the full Imms payload with ACTION_FLAG set to DELETE_LOGICAL
        # Only DELETE_PHYSICAL (REMOVE stream events) blanks Imms to ""
        self.assertNotEqual(item["Imms"], "", "DELETE_LOGICAL must retain Imms payload")
        self.assertIsInstance(item["Imms"], dict, "DELETE_LOGICAL Imms must be a dict (flat JSON)")
        self.assertEqual(
            item["Imms"].get("ACTION_FLAG"),
            ActionFlag.DELETE_LOGICAL,
            "DELETE_LOGICAL Imms must have ACTION_FLAG set to DELETE_LOGICAL",
        )

    def test_delete_physical_put_item_has_correct_timestamp_fields(self):
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE
        event = ValuesForTests.get_event(
            event_name=EventName.DELETE_PHYSICAL, operation=Operation.DELETE_PHYSICAL, imms_id="ts-del-phys"
        )
        handler(event, None)

        item = self._get_put_item_payload()
        self._assert_timestamp_fields(item)
        self.assertEqual(item["Operation"], Operation.DELETE_PHYSICAL)
        # DELETE_PHYSICAL (REMOVE stream event) blanks Imms to empty string
        self.assertEqual(item["Imms"], "", "Physical delete must blank out Imms")

    def test_missing_operation_on_modify_routes_to_dlq(self):
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE

        record = _make_stream_record(
            event_name="MODIFY",
            operation=None,  # Operation deliberately absent from NewImage
            patient_sk="covid#missing-op-id",
            sequence_number="49590338322303844748686548458181664417",
        )
        event = {"Records": [record]}
        result = handler(event, None)

        self.assertTrue(result)
        self.mock_delta_table.put_item.assert_not_called()
        self.mock_sqs_client.send_message.assert_called_once()
        dlq_call_kwargs = self.mock_sqs_client.send_message.call_args.kwargs
        self.assertEqual(dlq_call_kwargs["QueueUrl"], TEST_DEAD_LETTER_QUEUE_URL)


class TestGetCreationAndExpiryTimesWithSequence(unittest.TestCase):
    def test_get_creation_and_expiry_times(self):
        """Test that the function returns datetime_iso and expiry_timestamp (2-tuple)."""

        creation_timestamp = 1708264245.0  # 2024-02-18 14:30:45 UTC

        datetime_iso, expiry_timestamp = get_creation_and_expiry_times(creation_timestamp)

        from datetime import UTC, datetime

        expected_datetime = datetime.fromtimestamp(creation_timestamp, UTC).isoformat()
        self.assertEqual(datetime_iso, expected_datetime)

        expected_expiry = int(creation_timestamp) + (14 * 24 * 60 * 60)
        self.assertEqual(expiry_timestamp, expected_expiry)

    def test_datetime_stamp_lexicographic_ordering(self):
        """
        DateTimeStamp (ISO8601) sorts correctly across different seconds.
        """

        ts1 = 1708264245.0
        ts2 = 1708264246.0  # one second later

        dt1, _ = get_creation_and_expiry_times(ts1)
        dt2, _ = get_creation_and_expiry_times(ts2)

        self.assertLess(dt1, dt2, "Earlier timestamp must produce a lexicographically smaller DateTimeStamp")

    def test_sequence_number_ordering_independent_of_timestamp(self):
        """
        Verify that SequenceNumber strings from DynamoDB streams sort correctly
        when used as the tie-break in OperationSequenceIndex.
        """
        seq1 = "49590338322303844748686548458181664417"
        seq2 = "49590338322303844748686548458181664418"

        self.assertLess(seq1, seq2, "SequenceNumber must sort lexicographically for correct tie-break ordering")

        unsorted = [seq2, seq1]
        sorted_seqs = sorted(unsorted)
        self.assertEqual(sorted_seqs, [seq1, seq2])

    def test_expiry_is_ttl_days_from_creation(self):
        """ExpiresAt must be exactly DELTA_TTL_DAYS * 86400 seconds from creation."""

        creation_timestamp = 1708264245.0
        _, expiry_timestamp = get_creation_and_expiry_times(creation_timestamp)

        expected_expiry = int(creation_timestamp) + (14 * 24 * 60 * 60)
        self.assertEqual(expiry_timestamp, expected_expiry)


class DeltaRecordProcessorTestCase(unittest.TestCase):
    def setUp(self):
        self.logger_patcher = patch("delta.logger", make_mock_logger())
        self.mock_logger = self.logger_patcher.start()

        self.mock_delta_table = MagicMock()
        self.mock_sqs_client = MagicMock()

        self.get_delta_table_patcher = patch("delta.get_delta_table", return_value=self.mock_delta_table)
        self.get_delta_table_patcher.start()

    def tearDown(self):
        patch.stopall()

    def _call_process_record(self, record):
        return process_record(
            record,
            self.mock_delta_table,
        )

    def test_multi_record_success(self):
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE

        records = [
            _make_stream_record(
                event_name="INSERT", operation=Operation.CREATE, patient_sk="covid#ok-id-1", imms='{"a":1.1}'
            ),
            _make_stream_record(
                event_name="MODIFY", operation=Operation.UPDATE, patient_sk="covid#ok-id-2", imms='{"b":2.2}'
            ),
            _make_stream_record(event_name="REMOVE", operation=None, patient_sk="covid#ok-id-3", imms='{"c":3.3}'),
        ]

        for idx, record in enumerate(records, start=1):
            success, outcome = self._call_process_record(record)
            self.assertTrue(success)
            self.assertIn("record", outcome)
            self.assertIn("operation_type", outcome)
            self.assertEqual(self.mock_delta_table.put_item.call_count, idx)

        self.mock_sqs_client.send_message.assert_not_called()

    def test_multi_record_success_with_fail(self):
        self.mock_delta_table.put_item.side_effect = [
            SUCCESS_RESPONSE,
            ClientError({"Error": {"Code": "InternalServerError"}}, "PutItem"),
            SUCCESS_RESPONSE,
        ]

        records = [
            _make_stream_record(
                event_name="INSERT", operation=Operation.CREATE, patient_sk="covid#ok-id-1", imms_id="ok-id-1"
            ),
            _make_stream_record(
                event_name="MODIFY", operation=Operation.UPDATE, patient_sk="covid#fail-id-2", imms_id="fail-id-2"
            ),
            _make_stream_record(event_name="REMOVE", operation=None, patient_sk="covid#ok-id-3", imms_id="ok-id-3"),
        ]

        outcomes = [self._call_process_record(r) for r in records]

        self.assertEqual(self.mock_delta_table.put_item.call_count, 3)
        self.assertTrue(outcomes[0][0])
        self.assertFalse(outcomes[1][0])
        # record IS known — normalization succeeded, only put_item failed
        self.assertEqual(outcomes[1][1]["record"], "fail-id-2")
        self.assertEqual(outcomes[1][1]["statusCode"], "500")
        self.assertTrue(outcomes[2][0])

    def test_single_record_table_exception(self):
        self.mock_delta_table.put_item.side_effect = ClientError({"Error": {"Code": "InternalServerError"}}, "PutItem")
        record = _make_stream_record(
            event_name="MODIFY",
            operation=Operation.UPDATE,
            patient_sk="covid#exception-id",
            imms='{"k": 1.23}',
            imms_id="exception-id",
        )
        success, operation_outcome = self._call_process_record(record)
        self.assertFalse(success)
        self.assertEqual(operation_outcome["operation_type"], Operation.UPDATE)
        self.assertEqual(operation_outcome["statusCode"], "500")
        self.assertEqual(operation_outcome["statusDesc"], "Exception")
        self.assertIn("record", operation_outcome)
        # record IS known — normalization succeeded
        self.assertEqual(operation_outcome["record"], "exception-id")
        self.assertEqual(self.mock_delta_table.put_item.call_count, 1)

    def test_failed_outcome_always_has_record_and_operation_type(self):
        self.mock_delta_table.put_item.side_effect = Exception("db exploded")
        record = _make_stream_record(
            patient_sk="covid#schema-check", event_name="INSERT", operation=Operation.CREATE, imms_id="schema-check-id"
        )
        success, outcome = self._call_process_record(record)
        self.assertFalse(success)
        self.assertIn("record", outcome)
        self.assertIn("operation_type", outcome)
        # record IS known — normalization succeeded before put_item exploded
        self.assertEqual(outcome["record"], "schema-check-id")
        self.assertEqual(outcome["operation_type"], Operation.CREATE)
        self.mock_logger.exception.assert_called()

    @patch("delta.json.loads")
    def test_json_loads_called_with_parse_float_decimal(self, mock_json_loads):
        mock_json_loads.return_value = {"foo": decimal.Decimal("1.23")}
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE

        record = _make_stream_record(
            event_name="MODIFY",
            operation=Operation.UPDATE,
            patient_sk="covid#id",
            imms=ValuesForTests.json_value_for_test,
        )

        success, _ = self._call_process_record(record)

        self.assertTrue(success)
        mock_json_loads.assert_any_call(
            ValuesForTests.json_value_for_test,
            parse_float=decimal.Decimal,
        )

    def test_real_production_event_shape(self):
        """Verify the handler correctly processes the real production event shape"""
        self.mock_delta_table.put_item.return_value = SUCCESS_RESPONSE

        with patch("delta.get_sqs_client", return_value=MagicMock()), patch("delta.send_log_to_firehose"):
            real_record = {
                "eventID": "3a3c4907ccf4f102e9ec88be141da1ad",
                "eventName": "INSERT",
                "dynamodb": {
                    "ApproximateCreationDateTime": 1772440658,
                    "Keys": {"PK": {"S": "Immunization#cad9af6e-52b7-4af1-b966-aea62dcfbee1"}},
                    "NewImage": {
                        "Version": {"N": "1"},
                        "PatientPK": {"S": "Patient#9000186048"},
                        "SupplierSystem": {"S": "RAVS"},
                        "Resource": {"S": '{"resourceType": "Immunization"}'},
                        "PatientSK": {"S": "RSV#cad9af6e-52b7-4af1-b966-aea62dcfbee1"},
                        "Operation": {"S": "CREATE"},
                        "PK": {"S": "Immunization#cad9af6e-52b7-4af1-b966-aea62dcfbee1"},
                        "IdentifierPK": {"S": "https://supplierABC/identifiers/vacc#test"},
                    },
                    "SequenceNumber": "31155100001024489563148111",
                    "SizeBytes": 4411,
                    "StreamViewType": "NEW_IMAGE",
                },
            }
            event = {"Records": [real_record]}
            result = handler(event, None)

        self.assertTrue(result)
        self.mock_delta_table.put_item.assert_called_once()
        item = self.mock_delta_table.put_item.call_args.kwargs["Item"]
        self.assertEqual(item["Operation"], "CREATE")
        self.assertEqual(item["VaccineType"], "rsv")
        self.assertEqual(item["ImmsID"], "cad9af6e-52b7-4af1-b966-aea62dcfbee1")
        self.assertEqual(item["SequenceNumber"], "31155100001024489563148111")


class TestGetDeltaTable(unittest.TestCase):
    def setUp(self):
        delta.delta_table = None

        self.get_dynamodb_table_patcher = patch("delta.get_dynamodb_table")
        self.mock_get_dynamodb_table = self.get_dynamodb_table_patcher.start()

        self.logger_info_patcher = patch("delta.logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

        self.logger_error_patcher = patch("delta.logger.error")
        self.mock_logger_error = self.logger_error_patcher.start()

    def tearDown(self):
        delta.delta_table = None
        patch.stopall()

    def test_returns_table_on_success(self):
        mock_table = MagicMock()
        self.mock_get_dynamodb_table.return_value = mock_table
        result = delta.get_delta_table()
        self.assertIs(result, mock_table)
        self.assertIs(delta.delta_table, mock_table)

    def test_returns_cached_table(self):
        mock_table = MagicMock()
        self.mock_get_dynamodb_table.return_value = mock_table
        delta.get_delta_table()
        delta.get_delta_table()
        # Called only once — second call uses cache
        self.mock_get_dynamodb_table.assert_called_once()

    def test_raises_on_exception(self):
        self.mock_get_dynamodb_table.side_effect = Exception("DynamoDB unavailable")
        with self.assertRaises(Exception, msg="DynamoDB unavailable"):
            delta.get_delta_table()


class TestActionFlagMappingContract(unittest.TestCase):
    def test_operation_update_equals_action_flag_update(self):
        self.assertEqual(Operation.UPDATE, ActionFlag.UPDATE)

    def test_operation_delete_logical_equals_action_flag_delete_logical(self):
        self.assertEqual(Operation.DELETE_LOGICAL, ActionFlag.DELETE_LOGICAL)
