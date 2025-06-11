from record_processor import record_processor
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
        # self.s3_client_get_object_patcher = patch("record_processor.s3_client.get_object")
        # self.mock_s3_client_get_object = self.s3_client_get_object_patcher.start()
        self.redis_cacher_upload_patcher = patch("redis_cacher.RedisCacher.upload")
        self.mock_redis_cacher_upload = self.redis_cacher_upload_patcher.start()
        # mock S3Reader.read method
        # self.s3_reader_patcher = patch("record_processor.S3Reader.read")
        # self.mock_s3_reader_read = self.s3_reader_patcher.start()

    def tearDown(self):
        self.logger_info_patcher.stop()
        self.logger_error_patcher.stop()
        self.logger_exception_patcher.stop()
        # self.s3_client_get_object_patcher.stop()
        self.redis_cacher_upload_patcher.stop()
        # self.s3_reader_patcher.stop()

    def test_record_processor_success(self):
        # Test successful processing of a record
        # self.mock_s3_reader_read.return_value = self.mock_test_file
        self.mock_redis_cacher_upload.return_value = True
        result = record_processor(S3EventRecord(self.s3_vaccine))
        self.assertTrue(result)

    def test_record_processor_failure(self):
        # Test failure in processing a record
        # self.mock_s3_reader_read.return_value = self.mock_test_file
        self.mock_redis_cacher_upload.return_value = False
        result = record_processor(S3EventRecord(self.s3_vaccine))
        self.assertFalse(result)

    def test_record_processor_exception(self):
        # Test exception handling in record processing
        # self.mock_s3_reader_read.side_effect = Exception("Read error")
        self.mock_redis_cacher_upload.side_effect = Exception("Upload error")
        result = record_processor(S3EventRecord(self.s3_vaccine))
        self.assertFalse(result)
