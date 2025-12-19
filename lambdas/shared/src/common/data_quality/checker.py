from dataclasses import dataclass

from common.data_quality.completeness import DataQualityCompletenessChecker, MissingFields
from common.data_quality.validator import DataQualityValidator
from common.models.fhir_converter.converter import Converter


@dataclass
class DataQualityOutput:
    missing_fields: MissingFields
    invalid_fields: list[str]
    timeliness: dict[str, int]


class DataQualityChecker:
    """Runs data quality checks against an Immunisation and creates a Data Quality Output object"""

    def __init__(
        self,
        is_batch_csv: bool,
    ):
        self.is_batch_csv = is_batch_csv

    def run_checks(self, immunisation: dict) -> DataQualityOutput:
        fhir_converter = Converter(fhir_data=immunisation)
        completeness_checker = DataQualityCompletenessChecker()
        data_quality_validator = DataQualityValidator()

        if not self.is_batch_csv:
            immunisation = fhir_converter.run_conversion()

        return DataQualityOutput(
            missing_fields=self._check_completeness(immunisation, completeness_checker),
            invalid_fields=self._check_validity(immunisation, data_quality_validator),
            timeliness=self._check_timeliness(immunisation),
        )

    @staticmethod
    def _check_completeness(immunisation: dict, completeness_checker: DataQualityCompletenessChecker) -> MissingFields:
        return completeness_checker.check_completeness(immunisation)

    @staticmethod
    def _check_validity(immunisation: dict, data_quality_validator: DataQualityValidator) -> list[str]:
        pass

    @staticmethod
    def _check_timeliness(immunisation: dict) -> dict[str, int]:
        pass
