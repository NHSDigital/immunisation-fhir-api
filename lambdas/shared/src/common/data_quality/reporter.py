import json
import uuid
from dataclasses import asdict, dataclass

from botocore.exceptions import ClientError

from common.clients import get_s3_client, logger
from common.data_quality.checker import DataQualityChecker
from common.data_quality.completeness import MissingFields


@dataclass
class DataQualityReport:
    data_quality_report_id: uuid.UUID
    validationDate: str
    completeness: MissingFields
    validity: list[str]
    timeliness_recorded_days: int
    timeliness_ingested_seconds: int


class DataQualityReporter:
    """Generates and sends a data quality report to the relevant S3 bucket."""

    def __init__(self, is_batch_csv: bool, bucket: str):
        self.s3_client = get_s3_client()
        self.bucket = bucket
        self.dq_checker = DataQualityChecker(is_batch_csv=is_batch_csv)

    def generate_and_send_report(self, immunisation: dict) -> None:
        """Formats and sends a data quality report to the S3 bucket."""
        dq_output = self.dq_checker.run_checks(immunisation)
        event_id = uuid.uuid4()
        file_key = f"{event_id}.json"

        # Build report
        dq_report = DataQualityReport(
            data_quality_report_id=event_id,
            validationDate=dq_output.validation_datetime,
            completeness=dq_output.missing_fields,
            validity=dq_output.invalid_fields,
            timeliness_recorded_days=dq_output.timeliness.recorded_timeliness_days,
            timeliness_ingested_seconds=dq_output.timeliness.ingested_timeliness_seconds,
        )

        # Send to S3 bucket
        try:
            self.s3_client.put_object(
                Bucket=self.bucket, Key=file_key, Body=json.dumps(asdict(dq_report)), ContentType="application/json"
            )
        except ClientError as error:
            # We only log the error here because we want the data quality checks to have minimal impact on the API's
            # functionality. This should only happen in the case of AWS infrastructure issues.
            logger.error("error whilst sending data quality for report id: %s with error: %s", file_key, str(error))
            return None

        logger.info("data quality report sent successfully for report id: %s", file_key)

        return None
