import time
import unittest
from utils import (
    upload_file_to_s3,
    get_file_content_from_s3,
    check_ack_file_content,
    validate_row_count,
)

from clients import logger, sqs_client, batch_fifo_queue_url, ack_metadata_queue_url
from scenarios import scenarios, TestCases, TestCase

from constants import (
    SOURCE_BUCKET,
    INPUT_PREFIX,
    ACK_BUCKET,
    environment,
    DestinationType
)


class TestE2EBatch(unittest.TestCase):
    def setUp(self):
        test_data = TestCases(scenarios["dev"])
        test_data.enable_tests([
            "Successful Create",
            "Successful Update",
            "Successful Delete",
            "Create with 1252 char",
            "Failed Update",
            "Failed Delete",
        ])
        self.tests:  list[TestCase] = test_data.generate_csv_files_good()

    def tearDown(self):
        logger.info("Cleanup...")
        for test in self.tests:
            test.cleanup()

        try:
            # only purge if ENVIRONMENT=pr-* or dev
            if environment.startswith("pr-"):
                sqs_client.purge_queue(QueueUrl=batch_fifo_queue_url)
                sqs_client.purge_queue(QueueUrl=ack_metadata_queue_url)
        except sqs_client.exceptions.PurgeQueueInProgress:
            logger.error("SQS purge already in progress. Try again later.")
        except Exception as e:
            logger.error(f"SQS Purge error: {e}")

    @unittest.skipIf(environment == "ref", "Skip for ref")
    def test_batch_submission(self):
        """Test all scenarios and submit as batch."""
        start_time = time.time()
        max_timeout = 1200  # seconds)

        send_files(self.tests)

        if not poll_for_responses(self.tests, max_timeout):
            logger.error("Timeout waiting for responses")

        validate_responses(self.tests)

        logger.info(f"Tests Completed. Time: {time.time() - start_time:.1f} seconds")


def send_files(tests: list[TestCase]):
    start_time = time.time()
    for test in tests:
        if test.enabled:
            logger.info(f"Upload {test.file_name} ")
            key = upload_file_to_s3(test.file_name, SOURCE_BUCKET, INPUT_PREFIX)
            test.key = key
    logger.info(f"Files uploaded. Time: {time.time() - start_time:.1f} seconds")


def poll_for_responses(tests: list[TestCase], max_timeout=1200) -> bool:
    logger.info("Waiting while processing...")
    start_time = time.time()
    # while there are still pending files, poll for acks and forwarded files
    pending = True
    while pending:
        pending = False
        for test in tests:
            pending = test.get_poll_destinations(pending)
        if pending:
            print(".", end="")
            time.sleep(5)
        if (time.time() - start_time) > max_timeout:
            return False
    logger.info(f"Files processed. Time: {time.time() - start_time:.1f} seconds")
    return True


def validate_responses(tests: TestCases):
    start_time = time.time()
    count = 0
    expected_count = len(tests) * 2
    errors = False
    try:
        for test in tests:
            logger.info(f"Validation for Test: {test.name} ")
            # Validate the ACK file
            if test.ack_keys[DestinationType.INF]:
                count += 1
                inf_ack_content = get_file_content_from_s3(ACK_BUCKET, test.ack_keys[DestinationType.INF])
                check_ack_file_content(test.name, inf_ack_content, "Success", None,
                                       test.operation_outcome)
            else:
                logger.error(f"INF ACK file not found for test: {test.name}")
                errors = True

            if test.ack_keys[DestinationType.BUS]:
                count += 1
                validate_row_count(f"{test.name} - bus", test.file_name,
                                   test.ack_keys[DestinationType.BUS])

                test.check_bus_file_content()

                test.check_final_success_action()
            else:
                logger.error(f"BUS ACK file not found for test: {test.name}")
                errors = True

    except Exception as e:
        logger.error(f"Error during validation: {e}")
        errors = True
    finally:
        if count == expected_count:
            logger.info("All responses subject to validation.")
        else:
            logger.error(f"{count} of {expected_count} responses subject to validation.")
        logger.info(f"Time: {time.time() - start_time:.1f} seconds")
        assert count == expected_count, f"Only {count} of {expected_count} responses subject to validation."
        assert not errors, "Errors found during validation."
