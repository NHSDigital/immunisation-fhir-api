import unittest
import os
from io import BytesIO
from unittest.mock import patch
from utils_for_recordprocessor import dict_decode

with patch("logging_decorator.file_level_validation_logging_decorator", lambda f: f):
    # from file_level_validation import file_level_validation
    from batch_processor import process_csv_to_fhir


class TestProcessCsvToFhir(unittest.TestCase):

    def setUp(self):
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()
        self.update_audit_table_status_patcher = patch("batch_processor.update_audit_table_status")
        self.mock_update_audit_table_status = self.update_audit_table_status_patcher.start()
        self.send_to_kinesis_patcher = patch("batch_processor.send_to_kinesis")
        self.mock_send_to_kinesis = self.send_to_kinesis_patcher.start()
        self.map_target_disease_patcher = patch("batch_processor.map_target_disease")
        self.mock_map_target_disease = self.map_target_disease_patcher.start()
        self.s3_get_object_patcher = patch("utils_for_recordprocessor.s3_client.get_object")
        self.mock_s3_get_object = self.s3_get_object_patcher.start()
        self.make_and_move_patcher = patch("file_level_validation.make_and_upload_ack_file")
        self.mock_make_and_move = self.make_and_move_patcher.start()
        self.make_and_move_patcher = patch("file_level_validation.move_file")
        self.mock_move_file = self.make_and_move_patcher.start()
        # get_permitted_operations
        self.get_permitted_operations_patcher = patch("file_level_validation.get_permitted_operations")
        self.mock_get_permitted_operations = self.get_permitted_operations_patcher.start()

        # self.validate_content_headers_patcher = patch("file_level_validation.validate_content_headers")
        # self.mock_validate_content_headers = self.validate_content_headers_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_process_csv_to_fhir_success(self):
        # Setup mocks
        print("test_process_csv_to_fhir_success")
        try:
            test_csv_path = os.path.join(
                os.path.dirname(__file__), "test_data", "windows-1252-accented-e.csv"
            )
            with open(test_csv_path, "rb") as f:
                data = f.readlines()

            # insert source_text into last row of cp1252_bytes
            for i in reversed(range(len(data))):
                line = data[i]
                # Split fields by pipe
                fields = line.strip().split(b"|")
                print(f"replace field: {fields[2]}")
                fields[2] = b'D\xe9cembre'
                print(f"replaced field: {fields[2]}")

                # Reconstruct the line
                data[i] = b"|".join(fields) + b"\n"
                break

            # manually add

            # Read CSV from test_csv_path as utf-8
            ret1 = {"Body": BytesIO(b"".join(data))}
            ret2 = {"Body": BytesIO(b"".join(data))}
            self.mock_s3_get_object.side_effect = [ret1, ret2]
            self.mock_map_target_disease.return_value = "RSV"

            message_body = {
                        "message_id": "file123",
                        "vaccine_type": "covid",
                        "supplier": "test-supplier",
                        "filename": "file-key-1",
                        "permission": ["COVID.R", "COVID.U", "COVID.D"],
                        "allowed_operations": ["CREATE", "UPDATE", "DELETE"],
                        "created_at_formatted_string": "2024-09-05T12:00:00Z"
                        # "csv_dict_reader": csv_rows
                    }
            # self.mock_file_level_validation.return_value = message_body
            self.mock_get_permitted_operations.return_value = {"CREATE", "UPDATE", "DELETE"}

            self.mock_map_target_disease.return_value = "RSV"

            process_csv_to_fhir(message_body)
        except Exception as e:
            print(f"Exception during test: {e}")

    def test_fix_cp1252(self):
        # create a cp1252 string that contains an accented E
        source_text = b'D\xe9cembre'
        test_dict = {
            "date": source_text,
            "name": "Test Name"}
        utf8_dict = dict_decode(test_dict, "cp1252")
        self.assertEqual(utf8_dict["date"], "Décembre")
        self.assertEqual(utf8_dict["name"], "Test Name")
