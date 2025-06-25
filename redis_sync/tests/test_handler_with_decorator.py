''' unit tests for redis_sync.py '''
import unittest
import json
from unittest.mock import patch
from redis_sync import handler
from s3_event import S3EventRecord
from constants import RedisCacheKey


class TestHandlerDecorator(unittest.TestCase):
    """ Unit tests for the handler decorator in redis_sync.py
        these will check what is sent to firehose and the logging
        Note: test_handler.py will check the actual business logic of the handler
        the decorator is used to log the function execution and send logs to firehose
    """
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
        self.firehose_patcher = patch("log_decorator.firehose_client")
        self.mock_firehose_client = self.firehose_patcher.start()
        self.mock_firehose_client.put_record.return_value = True

    def tearDown(self):
        patch.stopall()

    def test_handler_decorator_success(self):
        mock_event = {'Records': [self.s3_vaccine]}
        self.mock_get_s3_records.return_value = [self.s3_vaccine]
        bucket_name = self.s3_vaccine['s3']['bucket']['name']
        file_key = self.s3_vaccine['s3']['object']['key']
        self.mock_record_processor.return_value = {'status': 'success',
                                                   'message': 'Successfully processed 1 records',
                                                   'bucket_name': bucket_name,
                                                   'file_key': file_key}

        handler(mock_event, None)

        # Get put_record arguments
        args, kwargs = self.mock_firehose_client.put_record.call_args
        record = kwargs.get("Record") or args[1]
        data_bytes = record["Data"]
        log_json = data_bytes.decode("utf-8")
        log_dict = json.loads(log_json)

        # check expected content
        event = log_dict["event"]
        self.assertIn("function_name", event)
        self.assertEqual(event["function_name"], "redis_sync_handler")
        self.assertEqual(event["status"], "success")
        self.assertEqual(event["message"], "Successfully processed 1 records")
        self.assertEqual(event["file_keys"], [file_key])

    def test_handler_decorator_failure(self):
        mock_event = {'Records': [self.s3_vaccine]}

        self.mock_get_s3_records.return_value = [self.s3_vaccine]
        bucket_name = self.s3_vaccine['s3']['bucket']['name']
        file_key = self.s3_vaccine['s3']['object']['key']
        with patch("redis_sync.process_record") as mock_record_processor:
            mock_record_processor.return_value = {'status': 'error',
                                                  'message': 'my-error',
                                                  'bucket_name': bucket_name,
                                                  'file_key': file_key}

            handler(mock_event, None)

            # Get put_record arguments
            args, kwargs = self.mock_firehose_client.put_record.call_args
            record = kwargs.get("Record") or args[1]
            data_bytes = record["Data"]
            log_json = data_bytes.decode("utf-8")
            log_dict = json.loads(log_json)
            # check expected content
            event = log_dict["event"]
            self.assertIn("function_name", event)
            self.assertEqual(event["function_name"], "redis_sync_handler")
            self.assertEqual(event["status"], "error")
            self.assertEqual(event["message"], 'Processed 1 records with 1 errors')
            self.assertEqual(event["file_keys"], [file_key])

    def test_handler_decorator_no_records1(self):
        mock_event = {'Records': []}

        self.mock_get_s3_records.return_value = []
        self.mock_record_processor.return_value = {'status': 'success', 'message': 'No records found in event'}

        handler(mock_event, None)

        # Get put_record arguments
        args, kwargs = self.mock_firehose_client.put_record.call_args
        record = kwargs.get("Record") or args[1]
        data_bytes = record["Data"]
        log_json = data_bytes.decode("utf-8")
        log_dict = json.loads(log_json)
        # check expected content
        event = log_dict["event"]
        self.assertIn("function_name", event)
        self.assertEqual(event["function_name"], "redis_sync_handler")
        self.assertEqual(event["status"], "success")
        # filename is empty since no records were processed
        self.assertEqual(event["message"], "No records found in event")
        self.assertNotIn("file_key", event)

    def test_handler_decorator_exception(self):
        mock_event = {'Records': [self.s3_vaccine]}
        self.mock_get_s3_records.side_effect = Exception("Test exception")

        handler(mock_event, None)

        # check put_record arguments
        args, kwargs = self.mock_firehose_client.put_record.call_args
        record = kwargs.get("Record") or args[1]
        data_bytes = record["Data"]
        log_json = data_bytes.decode("utf-8")
        log_dict = json.loads(log_json)
        # Now check for the expected content
        event = log_dict["event"]
        self.assertIn("function_name", event)
        self.assertEqual(event["function_name"], "redis_sync_handler")
        self.assertEqual(event["status"], "error")

    def test_handler_with_empty_event(self):
        self.mock_get_s3_records.return_value = []

        handler({}, None)

        # get put_record arguments
        args, kwargs = self.mock_firehose_client.put_record.call_args
        record = kwargs.get("Record") or args[1]
        data_bytes = record["Data"]
        log_json = data_bytes.decode("utf-8")
        log_dict = json.loads(log_json)
        # check expected content
        event = log_dict["event"]
        self.assertIn("function_name", event)
        self.assertEqual(event["function_name"], "redis_sync_handler")
        self.assertEqual(event["status"], "success")
        self.assertEqual(event["message"], "No records found in event")

    def test_handler_multi_record(self):
        mock_event = {'Records': [self.s3_vaccine, self.s3_supplier]}

        with patch.object(self.mock_get_s3_records,
                          "return_value", 
                          [S3EventRecord(self.s3_vaccine), S3EventRecord(self.s3_supplier)]):
            # repatch mock_record_processor
            with patch("redis_sync.process_record") as mock_record_processor:
                # Mock the return value for each record
                mock_record_processor.side_effect = [
                    {'status': 'success', 'message': 'Processed successfully',
                     'file_key': RedisCacheKey.DISEASE_MAPPING_FILE_KEY},
                    {'status': 'success', 'message': 'Processed successfully',
                     'file_key': RedisCacheKey.PERMISSIONS_CONFIG_FILE_KEY}
                ]

                handler(mock_event, None)

                # Get put_record arguments
                args, kwargs = self.mock_firehose_client.put_record.call_args
                record = kwargs.get("Record") or args[1]
                data_bytes = record["Data"]
                log_json = data_bytes.decode("utf-8")
                log_dict = json.loads(log_json)
                # check expected content
                event = log_dict["event"]
                self.assertIn("function_name", event)
                self.assertEqual(event["function_name"], "redis_sync_handler")
                self.assertEqual(event["status"], "success")

    # test to check that event_read is called when "read" key is passed in the event
    def test_handler_read_event(self):
        mock_event = {'read': 'myhash'}
        return_key = 'field1'
        return_value = 'value1'
        mock_read_event_response = {return_key: return_value}

        with patch('redis_sync.read_event') as mock_read_event:
            mock_read_event.return_value = mock_read_event_response
            handler(mock_event, None)

            # get put_record arguments
            args, kwargs = self.mock_firehose_client.put_record.call_args
            record = kwargs.get("Record") or args[1]
            data_bytes = record["Data"]
            log_json = data_bytes.decode("utf-8")
            log_dict = json.loads(log_json)
            # check expected content
            event = log_dict["event"]
            self.assertIn("function_name", event)
            self.assertEqual(event["function_name"], "redis_sync_handler")
            actual_return_value = event.get(return_key)
            self.assertEqual(actual_return_value, return_value)
