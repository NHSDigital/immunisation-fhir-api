from dataclasses import dataclass

from common.data_quality.completeness import DataQualityCompletenessChecker
from common.data_quality.validator import DataQualityValidator
from common.models.fhir_converter.converter import Converter
from common.models.fhir_converter.mappings import ActionFlag


@dataclass
class DataQualityOutput:
    incomplete_fields: dict[str, list[str]]
    invalid_fields: list[str]
    timeliness: dict[str, int]


class DataQualityChecker:
    """Runs data quality checks against an Immunisation and creates a Data Quality Output object"""

    def __init__(
        self,
        immunisation: dict,
        action_flag: ActionFlag,
        completeness_checker: DataQualityCompletenessChecker,
        data_quality_validator: DataQualityValidator,
        is_batch_csv: bool,
    ):
        self.immunisation = immunisation
        self.fhir_converter = Converter(fhir_data=immunisation, action_flag=action_flag)
        self.completeness_checker = completeness_checker
        self.data_quality_validator = data_quality_validator
        self.is_batch_csv = is_batch_csv

    def run_checks(self) -> DataQualityOutput:
        if not self.is_batch_csv:
            self.immunisation = self.fhir_converter.run_conversion()

        return DataQualityOutput(
            incomplete_fields=self._check_completeness(),
            invalid_fields=self._check_validity(),
            timeliness=self._check_timeliness(),
        )

    def _check_completeness(self) -> dict[str, list[str]]:
        pass

    def _check_validity(self) -> list[str]:
        pass

    def _check_timeliness(self) -> dict[str, int]:
        pass
