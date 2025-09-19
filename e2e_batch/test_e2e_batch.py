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
import logging


from constants import (
    SOURCE_BUCKET,
    INPUT_PREFIX,
    ACK_BUCKET,
    environment
)

CREATE = "CREATE"
UPDATE = "UPDATE"
DELETE = "DELETE"


seed_datas = [
    TestData("Create", "V0V8L", [CREATE]),
    TestData("Update", "8HK48", [CREATE, UPDATE]),
    TestData("Delete", "8HA94", [CREATE, UPDATE, DELETE]),
    TestData("Reinstate", "X26", [CREATE, DELETE, UPDATE]),
    # TestData("Update-Reinstate", "X8E5B", [CREATE, DELETE, UPDATE, UPDATE]),
    # TestData("Update-No Create", "YGM41", [UPDATE], success=False),
    # TestData("Delete-No Create", "YGJ", [DELETE], success=False),
    # TestData("Create with extended ascii characters in name", "YGA", [CREATE], inject_char=True),
]

logging.basicConfig(level="INFO")
logger = logging.getLogger()
logger.setLevel("INFO")


class TestE2EBatch(unittest.TestCase):

    @unittest.skipIf(environment == "ref", "Skip for ref")
    def test_create_success(self):
        """Test CREATE scenario."""
        start_time = time.time()
        max_timeout = 1200  # seconds

        test_datas: list[TestData] = generate_csv_files(seed_datas)

        for test in test_datas:

            key = upload_file_to_s3(test.file_name, SOURCE_BUCKET, INPUT_PREFIX)
            test.key = key

        # dictionary of file name to track whether inf and bus acks have been received
        start_time = time.time()
        # while there are still pending files, poll for acks and forwarded files
        pending = True
        while pending and (time.time() - start_time) < max_timeout:
            pending = False
            for test_data in test_datas:
                # loop through keys in test (inf and bus)
                for ack_key in test_data.ack_keys.keys():
                    if not test_data.ack_keys[ack_key]:
                        found_ack_key = poll_destination(test_data.file_name, ack_key)
                        if found_ack_key:
                            test_data.ack_keys[ack_key] = found_ack_key
                            logging.info(f"Found {ack_key} ack for {test_data.file_name}: {found_ack_key}")
                        else:
                            pending = True
            if pending:
                time.sleep(1)

        logging.info(f"Finished polling for acks. Time taken: {time.time() - start_time:.1f} seconds")

        # Now validate all files have been processed correctly
        for test_data in test_datas:
            # Validate the ACK file
            inf_ack_content = get_file_content_from_s3(ACK_BUCKET, test_data.ack_keys[DestinationType.INF])

            check_ack_file_content(inf_ack_content, "Success", None, test_data.actions)
            validate_row_count(test_data.file_name, test_data.ack_keys[DestinationType.BUS])
            # check row after header

            # how to validate bus ack content?
            # bus_ack_content = get_file_content_from_s3(ACK_BUCKET, test_data.ack_keys[DestinationType.BUS])

        logging.info(f"Completed all validations. Total time taken: {time.time() - start_time:.1f} seconds")

