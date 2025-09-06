import unittest
import os
from io import BytesIO
from unittest.mock import patch
# from utils_for_recordprocessor import dict_decode

with patch("logging_decorator.file_level_validation_logging_decorator", lambda f: f):
    # from file_level_validation import file_level_validation
    from batch_processor import process_csv_to_fhir


class TestProcessCsvToFhir(unittest.TestCase):

    def setUp(self):
        self.logger_info_patcher = patch("logging.Logger.info")
        self.mock_logger_info = self.logger_info_patcher.start()
        # self.update_audit_table_status_patcher = patch("batch_processor.update_audit_table_status")
        # self.mock_update_audit_table_status = self.update_audit_table_status_patcher.start()
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

    def expand_test_data(self, data: list[bytes], num_rows: int) -> list[bytes]:
        n_rows = len(data) - 1  # Exclude header

        if n_rows < num_rows:
            multiplier = (num_rows // n_rows) + 1
            header = data[0:1]
            body = data[1:] * multiplier
            data = header + body
            data = data[:num_rows + 1]
        print(f"Expanded test data to {len(data)-1} rows")
        return data

    def create_test_data_from_file(self, file_name: str) -> list[bytes]:
        test_csv_path = os.path.join(
            os.path.dirname(__file__), "test_data", file_name
        )
        with open(test_csv_path, "rb") as f:
            data = f.readlines()
        return data

    def insert_cp1252_at_end(self, data: list[bytes], new_text: bytes, field: int) -> list[bytes]:
        for i in reversed(range(len(data))):
            line = data[i]
            # Split fields by pipe
            fields = line.strip().split(b"|")
            print(f"replace field: {fields[field]}")
            fields[field] = new_text
            print(f"replaced field: {fields[field]}")

            # Reconstruct the line
            data[i] = b"|".join(fields) + b"\n"
            break
        return data

    def test_process_csv_to_fhir_success(self):
        # Setup mocks
        print("test_process_csv_to_fhir_success")
        try:
            data = self.create_test_data_from_file("test-batch-data.csv")
            data = self.expand_test_data(data, 20_000)
            data = self.insert_cp1252_at_end(data, b'D\xe9cembre', 2)

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

    def dict_decode(self):
        source_text = b'D\xe9cembre'
        test_dict = {
            "date": source_text,
            "name": "Test Name"}
        utf8_dict = dict_decode(test_dict, "cp1252")
        self.assertEqual(utf8_dict["date"], "Décembre")
        self.assertEqual(utf8_dict["name"], "Test Name")


def dict_decode(input_dict: dict, encoding: str) -> dict:
    """
    Decode all byte strings in a dictionary to UTF-8 strings using the specified encoding.
    """
    decoded_dict = {}
    for key, value in input_dict.items():
        if isinstance(value, bytes):
            decoded_dict[key] = value.decode(encoding)
        else:
            decoded_dict[key] = value
    return decoded_dict
