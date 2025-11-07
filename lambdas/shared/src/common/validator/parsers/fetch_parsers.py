from common.validator.parsers.csv_line_parser import CSVLineParser
from common.validator.parsers.fhir_parser import FHIRParser
from common.validator.parsers.schema_parser import SchemaParser


class FetchParsers:
    """
    Class responsible for fetching and managing different data parsers.
    """

    def __init__(self):
        self.parsers = {}

    # Retrieve all the Parsers, here we have CSVLineParser, CSVParser and FHIRParser
    def _get_csv_line_parser(self, csv_row, csv_header) -> CSVLineParser:
        csv_line_parser = CSVLineParser()
        csv_line_parser.parse_csv_line(csv_row, csv_header)
        return csv_line_parser

    def _get_fhir_parser(self, fhir_data: dict) -> FHIRParser:
        fhir_parser = FHIRParser()
        fhir_parser.parse_fhir_data(fhir_data)
        return fhir_parser

    def _get_schema_parser(self, schemafile: str) -> SchemaParser:
        schema_parser = SchemaParser()
        schema_parser.parse_schema(schemafile)
        return schema_parser
