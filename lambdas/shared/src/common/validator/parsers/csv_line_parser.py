# CSV Row importer and data access
import csv

class CSVLineParser:
    #parser variables
    CSVFileData = {}

    # parse the CSV into a Dictionary
    def parseCSVLine(self, CSVRow, CSVHeader):
        #create a key value mapping
        keys = list(csv.reader([CSVHeader]))[0]
        values  = list(csv.reader([CSVRow]))[0]
        self.CSVFileData = dict(map(lambda i,j : (i,j) , keys, values))


    #retrieve a column of data to work with
    def getKeyValues(self, fieldName):
            # creating empty lists, convery to list
            data = [self.CSVFileData[fieldName]]
            return data