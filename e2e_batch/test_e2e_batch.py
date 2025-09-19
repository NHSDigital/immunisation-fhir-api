import unittest
import time
from utils import (
    upload_file_to_s3,
    get_file_content_from_s3,
    check_ack_file_content,
    validate_row_count,
    generate_csv_files,
    TestData,
    poll_destination,
    DestinationType,
)

from constants import (
    SOURCE_BUCKET,
    INPUT_PREFIX,
    environment
)

CREATE = "CREATE"
UPDATE = "UPDATE"
DELETE = "DELETE"


seed_datas = [
    TestData("Create", "V0V8L", [CREATE]),
    # TestData("Update", "8HK48", [CREATE, UPDATE]),
    # TestData("Delete", "8HA94", [CREATE, UPDATE, DELETE]),
    # TestData("Reinstate", "X26", [CREATE, DELETE, UPDATE]),
    # TestData("Update-Reinstate", "X8E5B", [CREATE, DELETE, UPDATE, UPDATE]),
    # TestData("Update-No Create", "YGM41", [UPDATE], success=False),
    # TestData("Delete-No Create", "YGJ", [DELETE], success=False),
    # TestData("Create with extended ascii characters in name", "YGA", [CREATE], inject_char=True),
]


class TestE2EBatch(unittest.TestCase):

    @unittest.skipIf(environment == "ref", "Skip for ref")
    def test_create_success(self):
        """Test CREATE scenario."""
        max_timeout = 1200  # seconds

        test_datas: list[TestData] = generate_csv_files(seed_datas)

        for test in test_datas:

            key = upload_file_to_s3(test.file_name, SOURCE_BUCKET, INPUT_PREFIX)
            test.key = key

        # dictionary of file name to track whether inf and bus acks have been received
        pending = {test.file_name: {DestinationType.INF: True, DestinationType.BUS: True} for test in test_datas}

        start_time = time.time()
        # while there are still pending files, poll for acks and forwarded files
        while pending:
            for file_name in list(pending.keys()):
                test = pending[file_name]
                # loop through keys in test (inf and bus)
                for key in test.keys():
                    if test[key]:
                        is_pending = poll_destination(file_name, key)
                        if is_pending:
                            test[key] = False
            for file_name in list(pending.keys()):
                test = pending[file_name]
                # if both inf and bus are False, remove from pending
                if not test[DestinationType.INF] and not test[DestinationType.BUS]:
                    del pending[file_name]

            # if max_timeout exceeded, break
            if (time.time() - start_time) > max_timeout:
                break

            if pending:
                time.sleep(1)

        # Now validate all files have been processed correctly
        for test in test_datas:
            # Validate the ACK file
            ack_content = get_file_content_from_s3(environment.ACK_BUCKET, test.file_name)
            fwd_content = get_file_content_from_s3(environment.FORWARDEDFILE_BUCKET, test.fwd_key)

            check_ack_file_content(ack_content, "OK", None, test.action)
            validate_row_count(test.file_name, test.key)
            # Validate the forwarded file
            validate_row_count(test.file_name, test.key)
            check_ack_file_content(fwd_content, "OK", None, test.action)
