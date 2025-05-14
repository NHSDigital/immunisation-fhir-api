# Main validation engine

import ExceptionMessages
from FHIRParser import FHIRParser
from SchemaParser import SchemaParser
from ConversionChecker import ConversionChecker
import ConversionLayout
from datetime import datetime, timezone
from Extractor import (
    extract_person_names,
    extract_practitioner_names,
    extract_site_code,
    get_patient,
    get_valid_address,
)


# Converter
class Converter:

    def __init__(self, fhir_data):
        self.converted = {}
        self.error_records = []
        self.fhir_data = fhir_data  # Store JSON data directly
        self.schema_file = ConversionLayout.ConvertLayout

    # Utility logs tailored to conveter class errors
    def _log_error(self,e,code=ExceptionMessages.UNEXPECTED_EXCEPTION): 
        message = str(e)  # if a simple string message was passed 

        error_obj = {
            "code": code,
            "message": message
        }

        # if not any(existing.get("message") == message for existing in self.error_records):
        self.error_records.append(error_obj)
        return error_obj

    # create a FHIR  parser - uses fhir json data from delta 
    # (helper methods to extract values from the nested FHIR structure)
    def _getFHIRParser(self, fhir_data):
        fhirParser = FHIRParser()
        fhirParser.parseFHIRData(fhir_data)
        return fhirParser

    # create a schema parser - parses the schema that defines how FHIR fields should be mapped into flat fields.
    def _getSchemaParser(self, schemafile):
        schemaParser = SchemaParser()
        schemaParser.parseSchema(schemafile)
        return schemaParser

    # Convert data against converter schema
    def _convertData(self, ConversionValidate: ConversionChecker, expression, dataParser: FHIRParser, json_data):

        FHIRFieldName = expression["fieldNameFHIR"]
        FlatFieldName = expression["fieldNameFlat"]

        expressionType = expression["expression"]["expressionType"]
        expressionRule = expression["expression"]["expressionRule"]

        try:
            conversionValues = dataParser.getKeyValue(FHIRFieldName, expressionType, expressionRule)
        except Exception as e:
            message = "Data get value Unexpected exception [%s]: %s" % (e.__class__.__name__, e)
            error = self._log_error(message, code=ExceptionMessages.PARSING_ERROR)
            return error

        for conversionValue in conversionValues:
            convertedData = ConversionValidate.convertData(
                expressionType, expressionRule, FHIRFieldName, conversionValue
            )
            if "address" in FHIRFieldName or "performer" in FHIRFieldName or "name" in FHIRFieldName:
                convertedData = self.extract_patient_details(json_data, FlatFieldName)
            if convertedData is not None:
                self.converted[FlatFieldName] = convertedData

    # run the conversion against the data
    def runConversion(self, json_data, summarise=False, report_unexpected_exception=True):
        try:
            dataParser = self._getFHIRParser(self.fhir_data)
        except Exception as e:
            if report_unexpected_exception:
                message = "FHIR Parser Unexpected exception [%s]: %s" % (e.__class__.__name__, e)
                error = self._log_error(message,code=ExceptionMessages.UNEXPECTED_EXCEPTION)
                return error

        try:
            schemaParser = self._getSchemaParser(self.schema_file)
        except Exception as e:
            if report_unexpected_exception:
                message = "Schema Parser Unexpected exception [%s]: %s" % (e.__class__.__name__, e)
                error = self._log_error(message, code=ExceptionMessages.UNEXPECTED_EXCEPTION)
                return error

        try:
            ConversionValidate = ConversionChecker(dataParser, summarise, report_unexpected_exception)
        except Exception as e:
            if report_unexpected_exception:
                message = "Expression Checker Unexpected exception [%s]: %s" % (e.__class__.__name__, e)
                error = self._log_error(message, code=ExceptionMessages.UNEXPECTED_EXCEPTION)
                return error

        # get list of expressions
        try:
            conversions = schemaParser.getConversions()
        except Exception as e:
            if report_unexpected_exception:
                message = "Expression Getter Unexpected exception [%s]: %s" % (e.__class__.__name__, e)
                error = self._log_error(message, code=ExceptionMessages.UNEXPECTED_EXCEPTION)
                return error

        for conversion in conversions:
            rows = self._convertData(ConversionValidate, conversion, dataParser, json_data)
        
        # Collect and store any errors from ConversionChecker
        all_errors = ConversionValidate.get_error_records()
        self.error_records.extend(all_errors)

        # Add CONVERSION_ERRORS as the 35th field
        error_records = self.getErrorRecords()
        if error_records:
            error_summary = error_records
        else:
            error_summary = []
        self.converted["CONVERSION_ERRORS"] = error_summary

        return self.converted

    def getErrorRecords(self):
        return self.error_records

    def extract_patient_details(self, json_data, FlatFieldName):
        if not hasattr(self, "_cached_values"):
            self._cached_values = {}

        if not self._cached_values:
            try:
                occurrence_time = datetime.fromisoformat(json_data.get("occurrenceDateTime", ""))
                if occurrence_time and occurrence_time.tzinfo is None:
                    occurrence_time = occurrence_time.replace(tzinfo=timezone.utc)
            except Exception as e:
                    message = "DateTime conversion error [%s]: %s" % (e.__class__.__name__, e)
                    error = self._log_error(message, code=ExceptionMessages.UNEXPECTED_EXCEPTION)
                    return error
            patient = get_patient(json_data)
            if not patient:
                return None

            self._cached_values = {
                "PERSON_FORENAME": extract_person_names(patient, occurrence_time)[0],
                "PERSON_SURNAME": extract_person_names(patient, occurrence_time)[1],
                "PERSON_POSTCODE": get_valid_address(patient, occurrence_time),
                "SITE_CODE": extract_site_code(json_data)[0],
                "SITE_CODE_TYPE_URI": extract_site_code(json_data)[1],
                "PERFORMING_PROFESSIONAL_FORENAME": extract_practitioner_names(json_data, occurrence_time)[0],
                "PERFORMING_PROFESSIONAL_SURNAME": extract_practitioner_names(json_data, occurrence_time)[1]
            }

        return self._cached_values.get(FlatFieldName)