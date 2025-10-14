# CSV Row importer and data access
import csv


class CSVLineParser:
    # parser variables
    def __init__(self):
        self.csv_file_data = {}

    # parse the CSV into a Dictionary
    def parse_csv_line(self, csv_row, csv_header):
        # create a key value mapping
        keys = list(csv.reader([csv_header]))[0]
        values = list(csv.reader([csv_row]))[0]
        self.csv_file_data = dict(map(lambda i, j: (i, j), keys, values))

    # retrieve a column of data to work with
    def get_key_value(self, field_name):
        # creating empty lists, convert to list
        data = [self.csv_file_data[field_name]]
        return data
