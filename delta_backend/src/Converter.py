# Main validation engine

import ExceptionMessages
from FHIRParser import FHIRParser
from SchemaParser import SchemaParser
from ConversionChecker import ConversionChecker
import ConversionLayout

# Converter variables
FilePath = ""
SchemaFile = {}
imms = []
Converted = {}
ErrorRecords = []


# Converter
class Converter:

    def __init__(self, fhir_data):
        self.FHIRData = fhir_data  # Store JSON data directly
        self.SchemaFile = ConversionLayout.ConvertLayout

    # create a FHIR  parser - uses fhir json data from delta
    def _getFHIRParser(self, fhir_data):
        fhirParser = FHIRParser()
        fhirParser.parseFHIRData(fhir_data)
        return fhirParser

    # create a schema parser
    def _getSchemaParser(self, schemafile):
        schemaParser = SchemaParser()
        schemaParser.parseSchema(schemafile)
        return schemaParser

    # Convert data against converter schema
    def _convertData(self, ConversionValidate, expression, dataParser):

        FHIRFieldName = expression["fieldNameFHIR"]
        FlatFieldName = expression["fieldNameFlat"]

        expressionType = expression["expression"]["expressionType"]
        expressionRule = expression["expression"]["expressionRule"]

        try:
            conversionValues = dataParser.getKeyValue(FHIRFieldName)
        except Exception as e:
            message = "Data get value Unexpected exception [%s]: %s" % (e.__class__.__name__, e)
            p = {"code": ExceptionMessages.PARSING_ERROR, "message": message}
            ErrorRecords.append(p)
            return p

        for conversionValue in conversionValues:
            convertedData = ConversionValidate.convertData(
                expressionType, expressionRule, FHIRFieldName, conversionValue
            )
            if convertedData is not None:
                Converted[FlatFieldName] = convertedData

    # run the conversion against the data
    def runConversion(self, summarise=False, report_unexpected_exception=True):
        try:
            dataParser = self._getFHIRParser(self.FHIRData)
        except Exception as e:
            if report_unexpected_exception:
                message = "FHIR Parser Unexpected exception [%s]: %s" % (e.__class__.__name__, e)
                p = {"code": 0, "message": message}
                ErrorRecords.append(p)
                return p

        try:
            schemaParser = self._getSchemaParser(self.SchemaFile)
        except Exception as e:
            if report_unexpected_exception:
                message = "Schema Parser Unexpected exception [%s]: %s" % (e.__class__.__name__, e)
                p = {"code": 0, "message": message}
                ErrorRecords.append(p)
                return p

        try:
            ConversionValidate = ConversionChecker(dataParser, summarise, report_unexpected_exception)
        except Exception as e:
            if report_unexpected_exception:
                message = "Expression Checker Unexpected exception [%s]: %s" % (e.__class__.__name__, e)
                p = {"code": 0, "message": message}
                ErrorRecords.append(p)
                return p

        # get list of expressions
        try:
            conversions = schemaParser.getConversions()
        except Exception as e:
            if report_unexpected_exception:
                message = "Expression Getter Unexpected exception [%s]: %s" % (e.__class__.__name__, e)
                p = {"code": 0, "message": message}
                ErrorRecords.append(p)
                return p

        for conversion in conversions:
            rows = self._convertData(ConversionValidate, conversion, dataParser)

        imms.append(Converted)
        return imms

    def getErrorRecords(self):
        return ErrorRecords
