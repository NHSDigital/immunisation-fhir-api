from record_processor import process_record
import unittest
from unittest.mock import patch

from s3_event import S3EventRecord
from constants import RedisCacheKey


class TestRecordProcessor(unittest.TestCase):
    s3_vaccine = {
        'bucket': {'name': 'test-bucket1'},
        'object': {'key': RedisCacheKey.DISEASE_MAPPING_FILE_KEY}
    }
    s3_supplier = {
        'bucket': {'name': 'test-bucket1'},
        'object': {'key': RedisCacheKey.PERMISSIONS_CONFIG_FILE_KEY}
    }
    mock_test_file = {'a': 'test', 'b': 'test2'}

    def setUp(self):
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()
        self.logger_error_patcher = patch("logging.Logger.error")
        self.mock_logger_error = self.logger_error_patcher.start()
        self.logger_exception_patcher = patch("logging.Logger.exception")
        self.mock_logger_exception = self.logger_exception_patcher.start()
        self.redis_cacher_upload_patcher = patch("redis_cacher.RedisCacher.upload")
        self.mock_redis_cacher_upload = self.redis_cacher_upload_patcher.start()

    def tearDown(self):
        self.logger_info_patcher.stop()
        self.logger_error_patcher.stop()
        self.logger_exception_patcher.stop()
        self.redis_cacher_upload_patcher.stop()

    def test_record_processor_success(self):
        """ Test successful processing of a record """
        self.mock_redis_cacher_upload.return_value = {"status": "success"}

        result = process_record(S3EventRecord(self.s3_vaccine))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["bucket_name"], "test-bucket1")
        self.assertEqual(result["file_key"], RedisCacheKey.DISEASE_MAPPING_FILE_KEY)

    def test_record_processor_failure(self):
        """ Test failure in processing a record """
        self.mock_redis_cacher_upload.return_value = {"status": "error"}

        result = process_record(S3EventRecord(self.s3_vaccine))

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["bucket_name"], "test-bucket1")
        self.assertEqual(result["file_key"], RedisCacheKey.DISEASE_MAPPING_FILE_KEY)

    def test_record_processor_exception(self):
        """ Test exception handling in record processing """
        msg = "my error msg"
        self.mock_redis_cacher_upload.side_effect = Exception(msg)

        result = process_record(S3EventRecord(self.s3_vaccine))

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], msg)
        self.mock_logger_exception.assert_called_once_with("Error uploading to cache for filename '%s'",
                                                           RedisCacheKey.DISEASE_MAPPING_FILE_KEY)
