''' unit tests for redis_sync.py '''
import unittest
import importlib
from unittest.mock import patch
from constants import RedisCacheKey
import redis_sync


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
        with patch("log_decorator.logging_decorator", lambda prefix=None: (lambda f: f)):
            importlib.reload(redis_sync)
            mock_event = {'Records': [self.s3_vaccine]}
            self.mock_get_s3_records.return_value = [self.s3_vaccine]
            with patch("redis_sync.process_record") as mock_record_processor:
                mock_record_processor.return_value = {'status': 'success', 'message': 'Processed successfully',
                                                      'file_key': 'test-key'}
                result = redis_sync.handler(mock_event, None)
                self.assertEqual(result["status"], "success")
                self.assertEqual(result["message"], "Successfully processed 1 records")
                self.assertEqual(result["file_keys"], ['test-key'])

    def test_handler_failure(self):
        with patch("log_decorator.logging_decorator", lambda prefix=None: (lambda f: f)):
            importlib.reload(redis_sync)

            mock_event = {'Records': [self.s3_vaccine]}
            with patch("redis_sync.process_record") as mock_record_processor:
                self.mock_get_s3_records.return_value = [self.s3_vaccine]
                mock_record_processor.side_effect = Exception("Processing error 1")

                result = redis_sync.handler(mock_event, None)

                self.assertEqual(result, {'status': 'error', 'message': 'Error processing S3 event'})

    def test_handler_no_records(self):
        with patch("log_decorator.logging_decorator", lambda prefix=None: (lambda f: f)):
            importlib.reload(redis_sync)
            mock_event = {'Records': []}
            self.mock_get_s3_records.return_value = []
            result = redis_sync.handler(mock_event, None)
            self.assertEqual(result, {'status': 'success', 'message': 'No records found in event'})

    def test_handler_exception(self):
        with patch("log_decorator.logging_decorator", lambda prefix=None: (lambda f: f)):
            importlib.reload(redis_sync)
            mock_event = {'Records': [self.s3_vaccine]}
            self.mock_get_s3_records.return_value = [self.s3_vaccine]
            with patch("redis_sync.process_record") as mock_record_processor:
                mock_record_processor.side_effect = Exception("Processing error 2")
                result = redis_sync.handler(mock_event, None)
                self.assertEqual(result, {'status': 'error', 'message': 'Error processing S3 event'})

    def test_handler_with_empty_event(self):
        with patch("log_decorator.logging_decorator", lambda prefix=None: (lambda f: f)):
            importlib.reload(redis_sync)
            self.mock_get_s3_records.return_value = []
            result = redis_sync.handler({}, None)
            self.assertEqual(result, {'status': 'success', 'message': 'No records found in event'})

    def test_handler_multi_record(self):
        with patch("log_decorator.logging_decorator", lambda prefix=None: (lambda f: f)):
            importlib.reload(redis_sync)
            mock_event = {'Records': [self.s3_vaccine, self.s3_supplier]}
            # If you need S3EventRecord, uncomment the import and use it here
            # self.mock_get_s3_records.return_value = [
            #     S3EventRecord(self.s3_vaccine),
            #     S3EventRecord(self.s3_supplier)
            # ]
            self.mock_get_s3_records.return_value = [self.s3_vaccine, self.s3_supplier]
            with patch("redis_sync.process_record") as mock_record_processor:
                mock_record_processor.side_effect = [{'status': 'success', 'message': 'Processed successfully',
                                                      'file_key': 'test-key1'},
                                                     {'status': 'success', 'message': 'Processed successfully',
                                                     'file_key': 'test-key2'}]
                result = redis_sync.handler(mock_event, None)
                self.assertEqual(result['status'], 'success')
                self.assertEqual(result['message'], 'Successfully processed 2 records')
                self.assertEqual(result['file_keys'][0], 'test-key1')
                self.assertEqual(result['file_keys'][1], 'test-key2')

    def test_handler_read_event(self):
        with patch("log_decorator.logging_decorator", lambda prefix=None: (lambda f: f)):
            importlib.reload(redis_sync)
            mock_event = {'read': 'myhash'}
            mock_read_event_response = {'field1': 'value1'}
            with patch('redis_sync.read_event') as mock_read_event:
                mock_read_event.return_value = mock_read_event_response
                result = redis_sync.handler(mock_event, None)
                mock_read_event.assert_called_once()
                self.assertEqual(result, mock_read_event_response)
