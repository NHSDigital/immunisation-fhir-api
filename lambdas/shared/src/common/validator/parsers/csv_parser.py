# CSV importer and data access
import csv

class CSVParser:
    #parser variables
    CSVFileData = {}

#---------------------------------------------
# File Management 

    # parse the CSV into a Dictionary
    def parseCSVFile(self, CSVFileName):
        input_file = csv.DictReader(open(CSVFileName))
        self.CSVFileData = {elem: [] for elem in input_file.fieldnames}
        for row in input_file:
            for key in self.CSVFileData.keys():
                self.CSVFileData[key].append(row[key])

#---------------------------------------------
#Scan and retrieve values

    #retrieve a column of data to work with
    def getKeyValues(self, fieldName):
            # creating empty lists
            data = self.CSVFileData[fieldName]
            return data