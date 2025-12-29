import json
import uuid
from dataclasses import asdict, dataclass

from botocore.exceptions import ClientError

from common.clients import get_s3_client, logger
from common.data_quality.checker import DataQualityChecker
from common.data_quality.completeness import MissingFields


@dataclass
class DataQualityReport:
    data_quality_report_id: str
    validation_date: str
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
        dq_report_id = str(uuid.uuid4())
        file_key = f"{dq_report_id}.json"

        dq_report = DataQualityReport(
            data_quality_report_id=dq_report_id,
            validation_date=dq_output.validation_datetime,
            completeness=dq_output.missing_fields,
            validity=dq_output.invalid_fields,
            timeliness_recorded_days=dq_output.timeliness.recorded_timeliness_days,
            timeliness_ingested_seconds=dq_output.timeliness.ingested_timeliness_seconds,
        )

        try:
            # Do we need to consider adding a date to the file key? Depends on if it is useful for DQ team
            self.s3_client.put_object(
                Bucket=self.bucket, Key=file_key, Body=json.dumps(asdict(dq_report)), ContentType="application/json"
            )
        except ClientError as error:
            # We log but suppress the error as DQ is a non-critical part of the system vs. API functionality. This would
            # only occur in the rare event of infrastructure issues.
            logger.error("Error sending data quality report with ID: %s. Error: %s", dq_report_id, str(error))
            return None

        logger.info("Data quality report sent successfully with ID: %s", dq_report_id)
        return None
