import unittest
from utils import (
    upload_file_to_s3,
    get_file_content_from_s3,
    wait_for_ack_file,
    check_ack_file_content,
    validate_row_count,
    delete_file_from_s3,
    generate_csv_files,
    SeedTestData
)

from constants import (
    SOURCE_BUCKET,
    INPUT_PREFIX,
    ACK_BUCKET,
    environment
)

CREATE = "CREATE"
UPDATE = "UPDATE"
DELETE = "DELETE"


ods_vaccines = {
    "DPSFULL": ["3IN1", "COVID19", "FLU", "HPV", "MENACWY", "MMR", "RSV"],
    "DPSREDUCED": ["3IN1", "COVID19", "FLU", "HPV", "MENACWY", "MMR", "RSV"],
    "V0V8L": ["3IN1", "FLU", "HPV", "MENACWY", "MMR"],
    "8HK48": ["FLU"],
    "8HA94": ["COVID19"],
    "X26": ["MMR", "RSV"],
    "X8E5B": ["MMR", "RSV"],
    "YGM41": ["3IN1", "COVID19", "HPV", "MENACWY", "MMR", "RSV"],
    "YGJ": ["3IN1", "COVID19", "HPV", "MENACWY", "MMR", "RSV"],
    "YGA": ["3IN1", "HPV", "MENACWY", "MMR", "RSV"],
    "YGMYW": ["3IN1", "HPV", "MENACWY", "MMR", "RSV"],
}

seed_datas = [
    SeedTestData("Create", "V0V8L", [CREATE]),
    SeedTestData("Update", "8HK48", [CREATE, UPDATE]),
    SeedTestData("Delete", "8HA94", [CREATE, UPDATE, DELETE]),
    SeedTestData("Reinstate", "X26", [CREATE, DELETE, UPDATE]),
    SeedTestData("Update-Reinstate", "X8E5B", [CREATE, DELETE, UPDATE, UPDATE]),
    SeedTestData("Update-No Create", "YGM41", [UPDATE], success=False),
    SeedTestData("Delete-No Create", "YGJ", [DELETE], success=False),
    SeedTestData("Create with extended ascii characters in name", "YGA", [CREATE], inject_char=True),
]


class TestE2EBatch(unittest.TestCase):

    @unittest.skipIf(environment == "ref")
    def test_create_success(self):
        """Test CREATE scenario."""

        test_datas = generate_csv_files(seed_datas)

        for test in test_datas:
            key = upload_file_to_s3(test.file_name, SOURCE_BUCKET, INPUT_PREFIX)
            test.key = key

        for test in test_datas:
            ack_key = wait_for_ack_file(None, test.file_name, ACK_BUCKET, timeout=1200)
            self.ack_files.append(ack_key)

            validate_row_count(test.file_name, ack_key)

            ack_content = get_file_content_from_s3(ACK_BUCKET, ack_key)
            check_ack_file_content(ack_content, "OK", None, "CREATE")
