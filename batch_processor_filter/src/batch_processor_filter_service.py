"""Batch processor filter service module"""
import boto3
import json

from batch_audit_repository import BatchAuditRepository
from batch_file_created_event import BatchFileCreatedEvent
from batch_file_repository import BatchFileRepository
from constants import REGION_NAME, FileStatus, QUEUE_URL, FileNotProcessedReason
from exceptions import EventAlreadyProcessingForSupplierAndVaccTypeError
from logger import logger
from send_log_to_firehose import send_log_to_firehose


class BatchProcessorFilterService:
    """Batch processor filter service class. Provides the business logic for the Lambda function"""
    def __init__(
        self,
        audit_repo: BatchAuditRepository = BatchAuditRepository(),
        batch_file_repo: BatchFileRepository = BatchFileRepository()
    ):
        self._batch_audit_repository = audit_repo
        self._batch_file_repo = batch_file_repo
        self._queue_client = boto3.client('sqs', region_name=REGION_NAME)

    def _is_duplicate_file(self, file_key: str) -> bool:
        """Checks if a file with the same name has already been processed or marked for processing"""
        return self._batch_audit_repository.is_duplicate_file(file_key)

    def apply_filter(self, batch_file_created_event: BatchFileCreatedEvent) -> None:
        filename = batch_file_created_event["filename"]
        message_id = batch_file_created_event["message_id"]
        supplier = batch_file_created_event["supplier"]
        vaccine_type = batch_file_created_event["vaccine_type"]

        if self._is_duplicate_file(filename):
            # Mark as processed and return without error so next event will be picked up from queue
            logger.error("A duplicate file has already been processed. Filename: %s", filename)
            self._batch_audit_repository.update_status(
                message_id,
                f"{FileStatus.NOT_PROCESSED} - {FileNotProcessedReason.DUPLICATE}"
            )
            self._batch_file_repo.upload_failure_ack(batch_file_created_event)
            self._batch_file_repo.move_source_file_to_archive(filename)
            return

        if self._batch_audit_repository.is_event_processing_or_failed_for_supplier_and_vacc_type(
            supplier,
            vaccine_type
        ):
            # Raise error so event is returned to queue and retried again later
            logger.info("Batch event already processing for supplier and vacc type. Filename: %s", filename)
            raise EventAlreadyProcessingForSupplierAndVaccTypeError(f"Batch event already processing for supplier: "
                                                                    f"{supplier} and vacc type: {vaccine_type}")

        self._queue_client.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(batch_file_created_event),
            MessageGroupId=f"{supplier}_{vaccine_type}"
        )
        self._batch_audit_repository.update_status(message_id, FileStatus.PROCESSING)

        successful_log_message = f"File forwarded for processing by ECS. Filename: {filename}"
        logger.info(successful_log_message)
        send_log_to_firehose({**batch_file_created_event, "message": successful_log_message})
