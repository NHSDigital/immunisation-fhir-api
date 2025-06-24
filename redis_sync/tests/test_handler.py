''' unit tests for redis_sync.py '''
import unittest
from unittest.mock import patch
# from redis_sync import handler
from s3_event import S3EventRecord
from constants import RedisCacheKey

with patch("redis_sync_log_decorator.redis_sync_logging_decorator", lambda prefix=None: (lambda f: f)):
    from redis_sync import handler


class TestHandler(unittest.TestCase):
    s3_vaccine = {
        's3': {
            'bucket': {'name': 'test-bucket1'},
            'object': {'key': RedisCacheKey.DISEASE_MAPPING_FILE_KEY}
        }
    }
    s3_supplier = {
        's3': {
            'bucket': {'name': 'test-bucket1'},
            'object': {'key': RedisCacheKey.PERMISSIONS_CONFIG_FILE_KEY}
        }
    }

    def setUp(self):
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()
        self.logger_error_patcher = patch("logging.Logger.error")
        self.mock_logger_error = self.logger_error_patcher.start()
        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()
        self.get_s3_records_patcher = patch("s3_event.S3Event.get_s3_records")
        self.mock_get_s3_records = self.get_s3_records_patcher.start()
        self.record_processor_patcher = patch("redis_sync.process_record")
        self.mock_record_processor = self.record_processor_patcher.start()

    def tearDown(self):
        self.logger_info_patcher.stop()
        self.get_s3_records_patcher.stop()
        self.record_processor_patcher.stop()
        self.logger_error_patcher.stop()
        self.logger_exception_patcher.stop()

    def test_handler_success(self):
        mock_event = {'Records': [self.s3_vaccine]}
        self.mock_get_s3_records.return_value = [self.s3_vaccine]
        self.mock_record_processor.return_value = {'status': 'success', 'message': 'Processed successfully'}

        result = handler(mock_event, None)

        self.assertEqual(result, {'status': 'success', 'message': 'Successfully processed 1 records'})

    def test_handler_failure(self):
        mock_event = {'Records': [self.s3_vaccine]}

        self.mock_get_s3_records.return_value = [self.s3_vaccine]
        self.mock_record_processor.side_effect = Exception("Processing error")

        result = handler(mock_event, None)

        self.assertEqual(result, {'status': 'error', 'message': 'Error processing S3 event'})

    def test_handler_no_records(self):
        mock_event = {'Records': []}

        self.mock_get_s3_records.return_value = []

        result = handler(mock_event, None)

        self.assertEqual(result, {'status': 'success', 'message': 'No records found in event'})

    def test_handler_exception(self):
        mock_event = {'Records': [self.s3_vaccine]}
        self.mock_get_s3_records.return_value = [self.s3_vaccine]
        self.mock_record_processor.side_effect = Exception("Processing error")

        result = handler(mock_event, None)

        self.assertEqual(result, {'status': 'error', 'message': 'Error processing S3 event'})
        self.mock_logger_info.assert_called_with("Processing S3 event with %d records", 1)

    def test_handler_with_empty_event(self):
        self.mock_get_s3_records.return_value = []

        result = handler({}, None)

        self.assertEqual(result, {'status': 'success', 'message': 'No records found in event'})

    def test_handler_multi_record(self):
        mock_event = {'Records': [self.s3_vaccine, self.s3_supplier]}

        self.mock_get_s3_records.return_value = [
            S3EventRecord(self.s3_vaccine),
            S3EventRecord(self.s3_supplier)
        ]
        self.mock_record_processor.return_value = {'status': 'success', 'message': 'Processed successfully'}

        result = handler(mock_event, None)

        self.assertEqual(result, {'status': 'success', 'message': 'Successfully processed 2 records'})

    # test to check that event_read is called when "read" key is passed in the event
    def test_handler_read_event(self):
        mock_event = {'read': 'myhash'}
        mock_read_event_response = {'field1': 'value1'}

        with patch('redis_sync.read_event') as mock_read_event:
            mock_read_event.return_value = mock_read_event_response
            result = handler(mock_event, None)

            mock_read_event.assert_called_once()
            self.assertEqual(result, mock_read_event_response)
