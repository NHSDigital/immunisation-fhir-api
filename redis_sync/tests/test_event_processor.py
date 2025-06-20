''' unit tests for redis_sync.py '''
import unittest
from unittest.mock import patch
from event_processor import event_processor
from s3_event import S3EventRecord
from constants import RedisCacheKey


class TestEventProcessor(unittest.TestCase):

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
        self.record_processor_patcher = patch("event_processor.record_processor")
        self.mock_record_processor = self.record_processor_patcher.start()

    def tearDown(self):
        self.logger_info_patcher.stop()
        self.get_s3_records_patcher.stop()
        self.record_processor_patcher.stop()
        self.logger_error_patcher.stop()
        self.logger_exception_patcher.stop()

    def test_event_processor_success(self):
        mock_event = {'Records': [self.s3_vaccine]}
        self.mock_get_s3_records.return_value = [self.s3_vaccine]

        result = event_processor(mock_event, None)

        self.assertTrue(result)
        self.mock_logger_info.assert_called_with("Successfully processed all %d records", 1)

    def test_event_processor_failure(self):
        mock_event = {'Records': [self.s3_vaccine]}

        self.mock_get_s3_records.return_value = [self.s3_vaccine]
        self.mock_record_processor.side_effect = Exception("Processing error")

        result = event_processor(mock_event, None)

        self.assertEqual(result, {'status': 'error', 'message': 'Error processing S3 event'})
        self.mock_logger_info.assert_called_with("Processing S3 event with %d records", 1)

    def test_event_processor_no_records(self):
        mock_event = {'Records': []}

        self.mock_get_s3_records.return_value = []

        result = event_processor(mock_event, None)

        self.assertTrue(result)
        self.mock_logger_info.assert_called_with("Successfully processed all %d records", 0)

    def test_event_processor_exception(self):
        mock_event = {'Records': [self.s3_vaccine]}
        self.mock_get_s3_records.return_value = [self.s3_vaccine]
        self.mock_record_processor.side_effect = Exception("Processing error")

        result = event_processor(mock_event, None)

        self.assertEqual(result, {'status': 'error', 'message': 'Error processing S3 event'})
        self.mock_logger_info.assert_called_with("Processing S3 event with %d records", 1)

    def test_event_processor_with_empty_event(self):
        self.mock_get_s3_records.return_value = []

        result = event_processor({}, None)

        self.assertEqual(result, {'status': 'success', 'message': 'No records found in event'})

    def test_event_processor_multi_record(self):
        mock_event = {'Records': [self.s3_vaccine, self.s3_supplier]}

        self.mock_get_s3_records.return_value = [
            S3EventRecord(self.s3_vaccine),
            S3EventRecord(self.s3_supplier)
        ]
        self.mock_record_processor.return_value = True

        result = event_processor(mock_event, None)

        self.assertTrue(result)
        self.mock_logger_info.assert_called_with("Processing S3 event with %d records", 2)

    # test to check that event_read is called when "read" key is passed in the event
    def test_event_processor_read_event(self):
        mock_event = {'read': 'myhash'}
        mock_read_event_response = {'field1': 'value1'}

        with patch('event_processor.read_event') as mock_read_event:
            mock_read_event.return_value = mock_read_event_response
            result = event_processor(mock_event, None)

            mock_read_event.assert_called_once()
            self.assertEqual(result, mock_read_event_response)
