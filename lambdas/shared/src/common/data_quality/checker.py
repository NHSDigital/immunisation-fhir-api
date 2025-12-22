from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import ValidationError

from common.data_quality.completeness import DataQualityCompletenessChecker, MissingFields
from common.data_quality.models.immunization_batch_row_model import ImmunizationBatchRowModel
from common.data_quality.timeliness import (
    TimelinessCheckOutput,
    get_ingested_timeliness_seconds,
    get_recorded_timeliness_days,
)
from common.models.fhir_converter.converter import Converter


@dataclass
class DataQualityOutput:
    missing_fields: MissingFields
    invalid_fields: list[str]
    timeliness: TimelinessCheckOutput
    validation_datetime: str


class DataQualityChecker:
    """Runs data quality checks against an Immunisation and creates a Data Quality Output object"""

    def __init__(
        self,
        is_batch_csv: bool,
    ):
        self.completeness_checker = DataQualityCompletenessChecker()
        self.data_quality_model = ImmunizationBatchRowModel
        self.is_batch_csv = is_batch_csv

    def run_checks(self, immunisation: dict) -> DataQualityOutput:
        dq_checks_executed_timestamp = datetime.now(timezone.utc)

        if not self.is_batch_csv:
            immunisation = Converter(fhir_data=immunisation).run_conversion()

        return DataQualityOutput(
            missing_fields=self._check_completeness(immunisation),
            invalid_fields=self._check_validity(immunisation),
            timeliness=self._check_timeliness(immunisation, dq_checks_executed_timestamp),
            validation_datetime=dq_checks_executed_timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        )

    def _check_completeness(self, immunisation: dict) -> MissingFields:
        return self.completeness_checker.run_checks(immunisation)

    def _check_validity(self, immunisation: dict) -> list[str]:
        """Checks the flat batch csv immunisation data structure against the fields and validation rules defined by the
        data quality team. Returns the fields that were invalid."""
        fields_with_errors = []

        try:
            self.data_quality_model.parse_obj(immunisation)
        except ValidationError as exc:
            for error in exc.errors():
                path_to_field_name = error.get("loc", [])

                if len(path_to_field_name) > 0:
                    # Model uses a flat structure, so all fields will have a depth of 0
                    fields_with_errors.append(path_to_field_name[0])

        return fields_with_errors

    @staticmethod
    def _check_timeliness(immunisation: dict, datetime_now: datetime) -> TimelinessCheckOutput:
        return TimelinessCheckOutput(
            recorded_timeliness_days=get_recorded_timeliness_days(immunisation),
            ingested_timeliness_seconds=get_ingested_timeliness_seconds(immunisation, datetime_now),
        )
