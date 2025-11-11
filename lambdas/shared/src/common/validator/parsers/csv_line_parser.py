"""
Parses the CSV, so each header name becomes a key,
and its corresponding cell value becomes the value.

csv_row : A single line of CSV data ("9011011,Tom,32").
csv_header : The header line defining column names
                    ("nhs_number,name,age").

Example:
    >>> parser = CSVLineParser()
    >>> parser.parse_csv_line("9011011,Tom,32", "nhs_number,name,age")
    >>> parser.csv_file_data
    {'nhs_number': '9011011', 'name': 'Tom', 'age': '32'}
"""


class CSVLineParser:
    # parser variables
    def __init__(self):
        self.csv_file_data: dict[str, str] = {}

    # parse the CSV into a Dictionary
    def parse_csv_line(self, csv_row: dict[str, str]) -> None:
        self.csv_file_data = csv_row

    # Retrieves the value of a specific column name as a list.
    def get_key_value(self, field_name: str) -> str:
        retrieve_column_value = self.csv_file_data[field_name]
        return retrieve_column_value
