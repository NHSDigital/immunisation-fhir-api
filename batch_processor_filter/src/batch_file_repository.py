"""Module for the batch file repository"""
from csv import writer
from io import StringIO, BytesIO

import boto3

from batch_file_created_event import BatchFileCreatedEvent
from constants import SOURCE_BUCKET_NAME, ACK_BUCKET_NAME


class BatchFileRepository:
    """Repository class to handle interactions with batch files e.g. management of the source and ack files"""
    _ARCHIVE_FILE_DIR: str = "archive"
    _SOURCE_BUCKET_NAME: str = SOURCE_BUCKET_NAME
    _ACK_BUCKET_NAME: str = ACK_BUCKET_NAME

    def __init__(self):
        self._s3_client = boto3.client('s3')

    @staticmethod
    def _create_ack_failure_data(batch_file_created_event: BatchFileCreatedEvent) -> dict:
        return {
            "MESSAGE_HEADER_ID": batch_file_created_event["message_id"],
            "HEADER_RESPONSE_CODE": "Failure",
            "ISSUE_SEVERITY": "Fatal",
            "ISSUE_CODE": "Fatal Error",
            "ISSUE_DETAILS_CODE": "10001",
            "RESPONSE_TYPE": "Technical",
            "RESPONSE_CODE": "10002",
            "RESPONSE_DISPLAY": "Infrastructure Level Response Value - Processing Error",
            "RECEIVED_TIME": batch_file_created_event["created_at_formatted_string"],
            "MAILBOX_FROM": "",  # VED-197 TODO: Leave blank for DPS, add mailbox if from mesh mailbox
            "LOCAL_ID": "",  # VED-197 TODO: Leave blank for DPS, add from ctl file if data picked up from MESH mailbox
            "MESSAGE_DELIVERY": False,
        }

    def move_source_file_to_archive(self, file_key: str) -> None:
        self._s3_client.copy_object(
            Bucket=self._SOURCE_BUCKET_NAME,
            CopySource={"Bucket": self._SOURCE_BUCKET_NAME, "Key": file_key},
            Key=f"{self._ARCHIVE_FILE_DIR}/{file_key}"
        )
        self._s3_client.delete_object(Bucket=self._SOURCE_BUCKET_NAME, Key=file_key)

    def upload_failure_ack(self, batch_file_created_event: BatchFileCreatedEvent) -> None:
        ack_failure_data = self._create_ack_failure_data(batch_file_created_event)

        ack_filename = ("ack/" + batch_file_created_event["filename"]
                        .replace(".csv", f"_InfAck_{batch_file_created_event['created_at_formatted_string']}.csv"))

        # Create CSV file with | delimiter, filetype .csv
        csv_buffer = StringIO()
        csv_writer = writer(csv_buffer, delimiter="|")
        csv_writer.writerow(list(ack_failure_data.keys()))
        csv_writer.writerow(list(ack_failure_data.values()))

        # Upload the CSV file to S3
        csv_buffer.seek(0)
        csv_bytes = BytesIO(csv_buffer.getvalue().encode("utf-8"))
        self._s3_client.upload_fileobj(csv_bytes, self._ACK_BUCKET_NAME, ack_filename)
