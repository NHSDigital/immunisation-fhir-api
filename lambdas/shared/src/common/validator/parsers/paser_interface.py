# validation_engine/sources/source_definitions.py

from abc import ABC, abstractmethod

from common.validator.parsers.csv_line_parser import CSVLineParser
from common.validator.parsers.fhir_parser import FHIRParser


class PaserInterface(ABC):
    """Defines a common interface for all data extractors."""

    @abstractmethod
    def extract_field_values(self, field_path: str) -> dict:
        pass

    @abstractmethod
    def get_data_format(self) -> str:
        pass

    @abstractmethod
    def _get_field_path_from_schema(self, schema_expressions: list[dict], common_key: str, data_format: str) -> str:
        pass


class FHIRInterface(PaserInterface):
    def __init__(self, fhir_data: dict):
        self.fhir_parser = FHIRParser()
        self.fhir_parser.parse_fhir_data(fhir_data)

    def get_data_format(self) -> str:
        return "fhir"

    def extract_field_values(self, field_path) -> list[str]:
        fhir_value = self.fhir_parser.get_fhir_value_list(field_path)
        return fhir_value

    def _get_field_path_from_schema(self, schema_expressions: list[dict], common_key: str, data_format: str) -> str:
        data_format = data_format.lower()
        for expr in schema_expressions:
            if expr.get("fieldNameFlat") == common_key or expr.get("fieldNameFHIR") == common_key:
                return expr.get("fieldNameFlat") if data_format == "batch" else expr.get("fieldNameFHIR")
        return ""


class BatchInterface(PaserInterface):
    def __init__(self, csv_row: str, csv_header: str):
        self.csv_line_parser = CSVLineParser()
        self.csv_line_parser.parse_csv_line(csv_row, csv_header)

    def get_data_format(self) -> str:
        return "batch"

    def extract_field_values(self, field_path) -> list[str]:
        csv_value = self.csv_line_parser.get_key_value(field_path)
        return csv_value

    def _get_field_path_from_schema(self, schema_expressions: list[dict], common_key: str, data_format: str) -> str:
        data_format = data_format.lower()
        for expression in schema_expressions:
            if expression.get("fieldNameFlat") == common_key or expression.get("fieldNameFHIR") == common_key:
                return expression.get("fieldNameFlat") if data_format == "batch" else expression.get("fieldNameFHIR")
        return ""
