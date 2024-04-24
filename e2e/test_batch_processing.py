import copy
import logging
import unittest
import uuid
from time import sleep

# import boto3
# from botocore.config import Config

# from utils.batch import BatchFile, base_headers, base_record, get_s3_source_name, get_cluster_name, \
#     download_report_file, get_s3_destination_name, CtlFile, CtlData

from utils.batch import BatchFile, base_headers, base_record, \
    CtlFile, CtlData

logger = logging.getLogger("batch")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)


def _wait_for_batch_processing(ecs_client, cluster: str):
    """wait for batch processing to finish in the given cluster by polling the ECS tasks status"""
    timeout_seconds = 120
    elapsed = 0
    logger.debug(f"waiting for tasks to finish in cluster: {cluster}")
    while elapsed <= timeout_seconds:
        response = ecs_client.list_tasks(
            cluster=cluster,
            desiredStatus='RUNNING'
        )
        num_tasks = len(response['taskArns'])
        if num_tasks == 0:
            break
        sleep(1)
        elapsed += 1
        if elapsed % 10 == 0:
            logger.debug(f"waiting for batch processing to finish, elapsed: {elapsed} seconds")

    if elapsed >= timeout_seconds:
        raise TimeoutError("Batch processing tasks did not finish in time")


def make_ctl_file() -> CtlFile:
    ctl = CtlData(from_dts="a_date", to_dts="another_date")
    return CtlFile(ctl)


class TestBatchProcessing(unittest.TestCase):
    s3_client = None
    dat_key = None
    ctl_key = None
    report_key = None

    # @classmethod
    # def setUpClass(cls):
    #     name = str(uuid.uuid4())
    #     cls.dat_key = f"{name}.dat"
    #     cls.ctl_key = f"{name}.ctl"
    #     cls.report_key = cls.dat_key

    #     session = boto3.Session(profile_name="apim-dev")
    #     aws_conf = Config(region_name="eu-west-2")
    #     s3_client = session.client("s3", config=aws_conf)
    #     cls.s3_client = s3_client

    #     source_bucket = get_s3_source_name()
    #     date_file = cls.make_batch_file()
    #     # date_file.upload_to_s3(cls.s3_client, source_bucket, cls.dat_key)
    #     date_file.upload_to_s3(cls.s3_client, source_bucket)
    #     ctl_file = make_ctl_file()
    #     # ctl_file.upload_to_s3(cls.s3_client, source_bucket, cls.ctl_key)
    #     ctl_file.upload_to_s3(cls.s3_client, source_bucket)

    #     logger.debug("waiting for the batch processing to finish")
    #     # wait for the event rule to start the task and then wait for the task to finish
    #     sleep(5)
    #     ecs_client = session.client('ecs', config=aws_conf)
    #     _wait_for_batch_processing(ecs_client, get_cluster_name())

    @staticmethod
    def make_batch_file() -> BatchFile:
        # Try to create records for each scenario because, it takes time for uploading
        # and waiting for the processing to finish.
        bf = BatchFile(headers=base_headers)
        logger.debug("creating batch file with headers:")
        logger.debug(base_headers)

        record1 = copy.deepcopy(base_record)
        record1["UNIQUE_ID"] = str(uuid.uuid4())
        bf.add_record(record1, "happy-path")

        record2 = copy.deepcopy(base_record)
        record2["UNIQUE_ID"] = str(uuid.uuid4())
        record2["PERSON_DOB"] = "bad-date"
        bf.add_record(record1, "error")

        logger.debug(bf.stream.getvalue().decode("utf-8"))
        return bf

    # def test_batch_file(self):
    #     report = download_report_file(self.s3_client, get_s3_destination_name(), self.report_key)
    #     logger.debug(f"report:\n{report}")

    #     lines = report.splitlines()
    #     self.assertEqual(len(lines), 1)
