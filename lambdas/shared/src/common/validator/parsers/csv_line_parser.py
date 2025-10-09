# CSV Row importer and data access
import csv


class CSVLineParser:
    # parser variables
    def __init__(self):
        self.csv_file_data = {}

    # parse the CSV into a Dictionary
    def parseCSVLine(self, CSVRow, CSVHeader):
        # create a key value mapping
        keys = list(csv.reader([CSVHeader]))[0]
        values = list(csv.reader([CSVRow]))[0]
        self.csv_file_data = dict(map(lambda i, j: (i, j), keys, values))

    # retrieve a column of data to work with
    def getKeyValues(self, fieldName):
        # creating empty lists, convert to list
        data = [self.csv_file_data[fieldName]]
        return data
