from abc import ABC, abstractmethod
from typing import Any

from common.validator.parsers.csv_line_parser import CSVLineParser
from common.validator.parsers.fhir_parser import FHIRParser


class BaseParser(ABC):
    """Defines a common interface for all data extractors."""

    @abstractmethod
    def extract_field_values(self, field_path: str) -> dict:
        pass

    @abstractmethod
    def get_data_format(self) -> str:
        pass


class FHIRInterface(BaseParser):
    def __init__(self, fhir_data: dict):
        self.fhir_parser = FHIRParser()
        self.fhir_parser.parse_fhir_data(fhir_data)

    def get_data_format(self) -> str:
        return "fhir"

    def extract_field_values(self, field_path) -> list[Any]:
        fhir_value = self.fhir_parser.get_fhir_value_list(field_path)
        return fhir_value


class BatchInterface(BaseParser):
    def __init__(self, csv_row: dict[str, str]):
        self.csv_line_parser = CSVLineParser()
        self.csv_line_parser.parse_csv_line(csv_row)

    def get_data_format(self) -> str:
        return "batch"

    def extract_field_values(self, field_path) -> list[str]:
        csv_value = self.csv_line_parser.get_key_value(field_path)
        return csv_value
