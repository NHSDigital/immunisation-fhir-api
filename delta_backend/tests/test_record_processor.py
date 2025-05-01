import unittest
from unittest.mock import patch, MagicMock
import os
import json
from helpers.mappings import OperationName, EventName, ActionFlag
from helpers.record_processor import RecordProcessor
from helpers.db_processor import DbProcessor
from sample_data.get_event import get_event_record

class TestRecordProcessor(unittest.TestCase):
    success_response = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def setUp(self):
        # Common setup if needed
        self.db_processor_patcher = patch("helpers.db_processor.DbProcessor")
        self.mock_db_processor_class = self.db_processor_patcher.start()
        self.mock_db_processor = self.mock_db_processor_class.return_value


        self.logger_patcher = patch("logging.Logger.info")
        self.mock_logger = self.logger_patcher.start()

        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()

        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()

        self.firehose_logger_patcher = patch("delta.firehose_logger")
        self.mock_firehose_logger = self.firehose_logger_patcher.start()

        self.processor = RecordProcessor(
            delta_table=None,
            delta_source="test_source",
            log_data={},
            db_processor=self.mock_db_processor,
            firehose_logger=self.mock_firehose_logger,
            firehose_log={},
            logger=self.mock_logger,
        )

    def tearDown(self):
        self.db_processor_patcher.stop()
        self.logger_patcher.stop()
        self.logger_exception_patcher.stop()
        self.logger_info_patcher.stop()
        self.mock_firehose_logger.stop()

    @staticmethod
    def get_pks(imms_id):
        return(imms_id, f"covid#{imms_id}")
    
    @patch("boto3.client")
    def test_send_message_success(self, mock_boto_client):
        ## Check a single message is sent to SQS successfully
        # Arrange
        self.mock_db_processor.write.return_value = (self.success_response, [])

        imms_id, pk = self.get_pks("123456")
        record = get_event_record(pk, event_name=EventName.CREATE, operation=OperationName.CREATE, supplier="EMIS")

        # Act
        response = self.processor.process_record(record)

        # Assert
        expected_operation_outcome = {
            "record": pk,
            "operation_type": ActionFlag.CREATE,
            "statusCode": "200",
            "statusDesc": "Successfully synched into delta",
        }
        self.processor.firehose_log["event"]["operation_outcome"] = expected_operation_outcome
        self.mock_firehose_logger.send_log.assert_called_once_with(self.processor.firehose_log)
        assert response == {"statusCode": 200, "body": "Records processed successfully"}
        self.mock_logger.info.assert_called_with(f"Record Successfully created for {imms_id}")

    # def test_handler_success_remove(self, mock_boto_resource, mock_write):
    def test_record_success_remove(self):
        # Arrange
        self.mock_db_processor.remove.return_value = self.success_response
        imms_id, pk = self.get_pks("123456")
        event = get_event_record(pk, event_name=EventName.DELETE_PHYSICAL, operation=OperationName.DELETE_PHYSICAL)

        # Act
        result = self.processor.process_record(event)

        # Assert
        self.mock_db_processor.remove.assert_called_once()
        args, _ = self.mock_db_processor.remove.call_args  # Extract positional arguments
        self.assertEqual(args[0], imms_id)  # First argument
        self.assertEqual(args[1], OperationName.DELETE_PHYSICAL)  # Second argument
        self.assertEqual(result["statusCode"], 200)

    # def test_handler_success_insert(self, mock_boto_resource, mock_write):
    def test_success_insert(self):
        # Arrange
        self.mock_db_processor.write.return_value = (self.success_response, [])
        suppliers = ["DPS", "EMIS"]
        for supplier in suppliers:
            event = get_event_record("covid#123456", supplier=supplier)
            # Act
            result = self.processor.process_record(event)

            # Assert
            self.assertEqual(result["statusCode"], 200)

if __name__ == "__main__":
    unittest.main()
