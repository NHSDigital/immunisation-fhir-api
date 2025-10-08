# Main validation engine

import validator.enums.exception_messages as ExceptionMessages
import validator.enums.error_levels as ErrorLevels
from validator.parsers.csv_parser import CSVParser
from validator.parsers.csv_line_parser import CSVLineParser
from validator.parsers.fhir_parser import FHIRParser
from validator.parsers.schema_parser import SchemaParser
from validator.validation_expression_checker import ExpressionChecker, ErrorReport
from validator.reporter.dq_reporter import DQReporter


FilePath = ''
JSONData = {}
SchemaFile = {}
CSVRow = ''
CSVHeader = ''
error_records: list[ErrorReport] = []
isCSV = True
dataType = 'FHIR'  # 'FHIR', 'FHIRJSON', 'CSV', 'CSVROW'
dataParser = any


class Validator:

    def __init__(self, filepath, JSONData, schemafile, CSVRow, CSVHeader, dataType):
        self.FilePath = filepath
        self.JSONData = JSONData
        self.SchemaFile = schemafile
        self.CSVRow = CSVRow
        self.CSVHeader = CSVHeader
        self.dataType = dataType

    def _getCSVLineParser(self, CSVRow, CSVHeader):
        csvParser = CSVLineParser()
        csvParser.parseCSVLine(CSVRow, CSVHeader)
        return csvParser

    def _getCSVParser(self, filepath):
        csvParser = CSVParser()
        csvParser.parseCSVFile(filepath)
        return csvParser

    def _getFHIRParser(self, filepath):
        fhirParser = FHIRParser()
        fhirParser.parseFHIRFile(filepath)
        return fhirParser

    def _getFHIRJSONParser(self, FHIRData):
        fhirParser = FHIRParser()
        fhirParser.parseFHIRData(FHIRData)
        return fhirParser

    def _getSchemaParser(self, schemafile):
        schemaParser = SchemaParser()
        schemaParser.parseSchema(schemafile)
        return schemaParser

    def _addErrorRecord(self, errorRecord: ErrorReport, expressionErrorGroup, expressionName, expressionId, errorLevel):
        if errorRecord is not None:
            errorRecord.errorGroup = expressionErrorGroup
            errorRecord.name = expressionName
            errorRecord.id = expressionId
            errorRecord.errorLevel = errorLevel
            error_records.append(errorRecord)

    # Function to help identify a parent failure in the error list
    def _checkErrorRecordForFailure(self, expressionId):
        for errorRecord in error_records:
            if (errorRecord.id == expressionId):
                return True
        return False

    #  validate a single expression against the data file
    def _validateExpression(self, ExpressionValidate, expression,
                            inc_header_in_row_count) -> ErrorReport | int:
        row = 1
        if inc_header_in_row_count:
            row = 2

        if self.isCSV:
            expressionFieldName = expression['fieldNameCSV']
        else:
            expressionFieldName = expression['fieldNameFHIR']

        expressionId = expression['expressionId']
        errorLevel = expression['errorLevel']
        expressionName = expression['expression']['expressionName']
        expressionType = expression['expression']['expressionType']
        expressionRule = expression['expression']['expressionRule']
        expressionErrorGroup = expression['errorGroup']

        # Check to see if the expression has a parent, if so did the parent validate
        if ('parentExpression' in expression):
            parentExpression = expression['parentExpression']
            if (self._checkErrorRecordForFailure(parentExpression)):
                errorRecord = {'code': ExceptionMessages.PARENT_FAILED,
                               'message': ExceptionMessages.MESSAGES[ExceptionMessages.PARENT_FAILED]
                               + ', Parent ID: ' + parentExpression}
                self._addErrorRecord(errorRecord, expressionErrorGroup, expressionName, expressionId, errorLevel)
                return errorRecord

        try:
            expressionValues = self.dataParser.getKeyValue(expressionFieldName)
        except Exception as e:
            message = 'Data get values Unexpected exception [%s]: %s' % (e.__class__.__name__, e)
            error_report = ErrorReport(code=ExceptionMessages.PARSING_ERROR, message=message)
            self._addErrorRecord(error_report, expressionErrorGroup, expressionName, expressionId, self.CriticalErrorLevel)
            return error_report

        for value in expressionValues:
            errorRecord: ErrorReport = ExpressionValidate.validateExpression(expressionType, expressionRule,
                                                                             expressionFieldName, value, row)
            if errorRecord is not None:
                self._addErrorRecord(errorRecord, expressionErrorGroup, expressionName, expressionId, errorLevel)
            row += 1
        return row

    # run the validation against the data
    def runValidation(self, summarise=False, report_unexpected_exception=True,
                      inc_header_in_row_count=True) -> list[ErrorReport]:
        try:
            error_records.clear()

            match self.dataType:  # 'FHIR', 'FHIRJSON', 'CSV', 'CSVROW'
                case 'FHIR':
                    self.dataParser = self._getFHIRParser(self.FilePath)
                    self.isCSV = False
                case 'FHIRJSON':
                    self.dataParser = self._getFHIRJSONParser(self.JSONData)
                    self.isCSV = False
                case 'CSV':
                    self.dataParser = self._getCSVParser(self.FilePath)
                    self.isCSV = True
                case 'CSVROW':
                    self.dataParser = self._getCSVLineParser(self.CSVRow, self.CSVHeader)
                    self.isCSV = True

        except Exception as e:
            if report_unexpected_exception:
                message = 'Data Parser Unexpected exception [%s]: %s' % (e.__class__.__name__, e)
                return [ErrorReport(code=0, message=message)]

        try:
            schemaParser = self._getSchemaParser(self.SchemaFile)
        except Exception as e:
            if report_unexpected_exception:
                message = 'Schema Parser Unexpected exception [%s]: %s' % (e.__class__.__name__, e)
                return [ErrorReport(code=0, message=message)]

        try:
            ExpressionValidate = ExpressionChecker(dataParser, summarise, report_unexpected_exception)
        except Exception as e:
            if report_unexpected_exception:
                message = 'Expression Checker Unexpected exception [%s]: %s' % (e.__class__.__name__, e)
                return [ErrorReport(code=0, message=message)]

        # get list of expressions
        try:
            expressions = schemaParser.getExpressions()
        except Exception as e:
            if report_unexpected_exception:
                message = 'Expression Getter Unexpected exception [%s]: %s' % (e.__class__.__name__, e)
                return [ErrorReport(code=0, message=message)]

        for expression in expressions:
            # rows = self._validateExpression(ExpressionValidate, expression, inc_header_in_row_count)
            self._validateExpression(ExpressionValidate, expression, inc_header_in_row_count)

        return error_records

    # -------------------------------------------------------------------------
    # Report Generation
    # Build the error Report
    def buildErrorReport(self, eventId):
        OccurrenceDateTime = self.dataParser.getKeySingleValue('occurrenceDateTime')
        dqReporter = DQReporter()
        dqReport = dqReporter.generateErrorReport(eventId, OccurrenceDateTime, error_records)

        return dqReport

    # Check all errors to see if we have a critical error that would fail the validation
    def hasValidationFailed(self):
        for errorRecord in error_records:
            if (errorRecord['errorLevel'] == ErrorLevels.CRITICAL_ERROR):
                return True
        return False
