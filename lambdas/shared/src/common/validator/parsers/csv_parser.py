# CSV importer and data access
import csv


class CSVParser:

    """ File Management"""
    # parser variables
    def __init__(self):
        self.csv_file_data = {}

    # parse the CSV into a Dictionary
    def parse_csv_file(self, csv_filename):
        input_file = csv.DictReader(open(csv_filename))
        self.csv_file_data = {elem: [] for elem in input_file.fieldnames}
        for row in input_file:
            for key in self.csv_file_data.keys():
                self.csv_file_data[key].append(row[key])

    # ---------------------------------------------
    # Scan and retrieve values
    # retrieve a column of data to work with
    def get_key_values(self, field_name):
        # creating empty lists
        data = self.csv_file_data[field_name]
        return data
