"""
Reads and parses the specified CSV file into a dictionary of lists.

Each key in the dictionary corresponds to a CSV column header, and
each value is a list containing all entries under that header.

csv_filename (str): The path to the CSV file to parse.
delimiter (str): The field delimiter used in the CSV file. Defaults to '|'.
"""

import csv


class CSVParser:
    def __init__(self):
        self.csv_file_data = {}

    # parse the CSV into a Dictionary
    """
    Takes a CSV file with numerous fields (that uses pipe delimiter) and parses it into a list of dictionaries using csv.DictReader.
    Then create a key for each header and attached a list of all the value to that key. So a one to many relationship 
    is created between the header and the values.
    """

    def parse_csv_file(self, csv_filename: str, delimiter: str = "|") -> None:
        with open(csv_filename, newline="", encoding="utf-8") as file:
            csv_to_dict = csv.DictReader(file, delimiter=delimiter)
            self.csv_file_data = {headers: [] for headers in csv_to_dict.fieldnames}
            csv_header_to_keys = self.csv_file_data.keys()
            for row in csv_to_dict:
                for key in csv_header_to_keys:
                    self.csv_file_data[key].append(row[key])

    """
    Retrieves all values associated with the specified column header (key).
    :param field_name: The column header whose values are to be retrieved.
    :return: A list of values under the specified column header or key.
    """

    # retrieve a column of data to work with
    def get_key_value(self, field_name: str) -> list[str]:
        retrieve_column_data = self.csv_file_data[field_name]
        return retrieve_column_data
