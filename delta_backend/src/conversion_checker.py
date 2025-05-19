
# Handles the transformation logic for each field based on the schema
# Root and base type expression checker functions
import exception_messages
from datetime import datetime,timedelta, timezone
import re

# --------------------------------------------------------------------------------------------------------
# Custom error type to handle validation failures
class RecordError(Exception):

    def __init__(self, code=None, message=None, details=None):
        self.code = code
        self.message = message
        self.details = details

    def __str__(self):
        return repr((self.code, self.message, self.details))

    def __repr__(self):
        return repr((self.code, self.message, self.details))

# ---------------------------------------------------------------------------------------------------------
# main conversion checker
# Conversion engine for expression-based field transformation
class ConversionChecker:
    # checker settings
    summarise = False
    report_unexpected_exception = True
    dataParser = any

    def __init__(self, dataParser, summarise, report_unexpected_exception):
        self.dataParser = dataParser  # FHIR data parser for additional functions
        self.summarise = summarise  # instance attribute
        self.report_unexpected_exception = report_unexpected_exception  # instance attribute
        self.errorRecords = []  # Store all errors here

    # Main entry point called by converter.py
    def convertData(self, expressionType, expressionRule, fieldName, fieldValue):
        match expressionType:
            case "DEFAULT":
                # TODO - check expression_rule is callable
                return expressionRule()
            case _:
                raise ValueError("Schema expression not found! Check your expression type : " + expressionType)

    # Utility function for logging errors
    def _log_error(self, fieldName, fieldValue, e, code=exception_messages.RECORD_CHECK_FAILED):
        if isinstance(e, Exception):
            message = exception_messages.MESSAGES[exception_messages.UNEXPECTED_EXCEPTION] % (e.__class__.__name__, str(e))
        else:
            message = str(e)  # if a simple string message was passed

        self.errorRecords.append({
            "code": code,
            "field": fieldName,
            "value": fieldValue,
            "message": message
        })
        
    def get_error_records(self):
        return self.errorRecords
