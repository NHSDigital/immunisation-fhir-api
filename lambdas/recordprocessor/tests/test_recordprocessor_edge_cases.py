import os
import unittest
from io import BytesIO
from unittest.mock import Mock, call, patch

from batch_processor import process_csv_to_fhir
from utils_for_recordprocessor_tests.utils_for_recordprocessor_tests import (
    BucketNames,
    create_patch,
)


class TestProcessorEdgeCases(unittest.TestCase):
    def setUp(self):
        self.mock_logger_info = create_patch("logging.Logger.info")
        self.mock_logger_warning = create_patch("logging.Logger.warning")
        self.mock_logger_error = create_patch("logging.Logger.error")
        self.mock_send_to_kinesis = create_patch("batch_processor.send_to_kinesis")
        self.mock_map_target_disease = create_patch("batch_processor.map_target_disease")
        self.mock_get_s3_client = create_patch("utils_for_recordprocessor.get_s3_client")
        self.mock_make_and_move = create_patch("file_level_validation.make_and_upload_ack_file")
        self.mock_move_file = create_patch("file_level_validation.move_file")
        self.mock_get_permitted_operations = create_patch("file_level_validation.get_permitted_operations")
        self.mock_firehose_client = create_patch("common.log_firehose.firehose_client")
        self.mock_update_audit_table_status = create_patch("batch_processor.update_audit_table_status")

    def tearDown(self):
        patch.stopall()

    def expand_test_data(self, data: list[bytes], num_rows: int) -> list[bytes]:
        n_rows = len(data) - 1  # Exclude header

        if n_rows < num_rows:
            multiplier = (num_rows // n_rows) + 1
            header = data[0:1]
            body = data[1:] * multiplier
            data = header + body
            data = data[: num_rows + 1]
        return data

    def create_test_data_from_file(self, file_name: str) -> list[bytes]:
        test_csv_path = os.path.join(os.path.dirname(__file__), "test_data", file_name)
        with open(test_csv_path, "rb") as f:
            data = f.readlines()
        return data

    def insert_cp1252_at_end(self, data: list[bytes], new_text: bytes, field: int) -> list[bytes]:
        for i in reversed(range(len(data))):
            line = data[i]
            # Split fields by pipe
            fields = line.strip().split(b"|")
            fields[field] = new_text
            # Reconstruct the line
            data[i] = b"|".join(fields) + b"\n"
            break
        return data

    def test_process_large_file_cp1252(self):
        """Test processing a large file with cp1252 encoding"""
        n_rows = 500
        data = self.create_test_data_from_file("test-batch-data.csv")
        data = self.expand_test_data(data, n_rows)
        data = self.insert_cp1252_at_end(data, b"D\xe9cembre", 2)
        ret1 = {"Body": BytesIO(b"".join(data))}
        ret2 = {"Body": BytesIO(b"".join(data))}
        mock_s3 = Mock()
        mock_s3.get_object.side_effect = [ret1, ret2]
        self.mock_get_s3_client.return_value = mock_s3
        self.mock_map_target_disease.return_value = "some disease"

        message_body = {
            "vaccine_type": "vax-type-1",
            "supplier": "test-supplier",
            "filename": "test-filename",
        }
        self.mock_map_target_disease.return_value = "some disease"

        n_rows_processed = process_csv_to_fhir(message_body)
        self.assertEqual(n_rows_processed, n_rows)
        self.assertEqual(self.mock_send_to_kinesis.call_count, n_rows)
        # check logger.warning called for decode error
        self.mock_logger_warning.assert_called()
        warning_call_args = self.mock_logger_warning.call_args[0][0]
        self.assertTrue(warning_call_args.startswith("Encoding Error: 'utf-8' codec can't decode byte 0xe9"))
        # TODO: when running all tests this expects Bucket=None. not clear why.
        mock_s3.get_object.assert_has_calls(
            [
                call(Bucket=BucketNames.SOURCE, Key="test-filename"),
                call(Bucket=BucketNames.SOURCE, Key="processing/test-filename"),
            ]
        )

    def test_process_large_file_utf8(self):
        """Test processing a large file with utf-8 encoding"""
        n_rows = 500
        data = self.create_test_data_from_file("test-batch-data.csv")
        data = self.expand_test_data(data, n_rows)
        ret1 = {"Body": BytesIO(b"".join(data))}
        ret2 = {"Body": BytesIO(b"".join(data))}
        mock_s3 = Mock()
        mock_s3.get_object.side_effect = [ret1, ret2]
        self.mock_get_s3_client.return_value = mock_s3
        self.mock_map_target_disease.return_value = "some disease"

        message_body = {
            "vaccine_type": "vax-type-1",
            "supplier": "test-supplier",
        }
        self.mock_map_target_disease.return_value = "some disease"

        n_rows_processed = process_csv_to_fhir(message_body)
        self.assertEqual(n_rows_processed, n_rows)
        self.assertEqual(self.mock_send_to_kinesis.call_count, n_rows)
        self.mock_logger_warning.assert_not_called()
        self.mock_logger_error.assert_not_called()

    def test_process_small_file_cp1252(self):
        """Test processing a small file with cp1252 encoding"""
        data = self.create_test_data_from_file("test-batch-data-cp1252.csv")
        data = self.insert_cp1252_at_end(data, b"D\xe9cembre", 2)
        data = [line if line.endswith(b"\n") else line + b"\n" for line in data]
        n_rows = len(data) - 1  # Exclude header

        ret1 = {"Body": BytesIO(b"".join(data))}
        ret2 = {"Body": BytesIO(b"".join(data))}
        mock_s3 = Mock()
        mock_s3.get_object.side_effect = [ret1, ret2]
        self.mock_get_s3_client.return_value = mock_s3
        self.mock_map_target_disease.return_value = "some disease"

        message_body = {
            "vaccine_type": "vax-type-1",
            "supplier": "test-supplier",
        }

        self.mock_map_target_disease.return_value = "some disease"

        n_rows_processed = process_csv_to_fhir(message_body)
        self.assertEqual(n_rows_processed, n_rows)
        self.assertEqual(self.mock_send_to_kinesis.call_count, n_rows)
        self.mock_logger_warning.assert_called()
        warning_call_args = self.mock_logger_warning.call_args[0][0]
        self.assertTrue(warning_call_args.startswith("Invalid Encoding detected"))

    def test_process_small_file_utf8(self):
        """Test processing a small file with utf-8 encoding"""
        data = self.create_test_data_from_file("test-batch-data.csv")
        data = [line if line.endswith(b"\n") else line + b"\n" for line in data]
        n_rows = len(data) - 1  # Exclude header

        ret1 = {"Body": BytesIO(b"".join(data))}
        ret2 = {"Body": BytesIO(b"".join(data))}
        mock_s3 = Mock()
        mock_s3.get_object.side_effect = [ret1, ret2]
        self.mock_get_s3_client.return_value = mock_s3
        self.mock_map_target_disease.return_value = "some disease"

        message_body = {
            "vaccine_type": "vax-type-1",
            "supplier": "test-supplier",
        }
        self.mock_map_target_disease.return_value = "some disease"

        n_rows_processed = process_csv_to_fhir(message_body)
        self.assertEqual(n_rows_processed, n_rows)
        self.assertEqual(self.mock_send_to_kinesis.call_count, n_rows)
        self.mock_logger_warning.assert_not_called()
        self.mock_logger_error.assert_not_called()
