# Main validation engine

import exception_messages
from fhir_parser import FHIRParser
from schema_parser import SchemaParser
from conversion_checker import ConversionChecker
from conversion_layout import ConversionLayout
from datetime import datetime, timezone
from json_field_extractor import Extractor


# Converter
class Converter:

    def __init__(self, fhir_data, action_flag = "UPDATE", summarise=False, report_unexpected_exception=True):
        self.converted = {}
        self.error_records = []
        self.action_flag = action_flag
        self.fhir_data = fhir_data
        self.summarise = summarise
        self.report_unexpected_exception = report_unexpected_exception

        try:
            conversion_layout = ConversionLayout(fhir_data)
            self.schema_file = conversion_layout.get_conversion_layout()
            
            self.data_parser = FHIRParser()
            self.data_parser.parseFHIRData(fhir_data)

            self.schema_parser = SchemaParser()
            self.schema_parser.parseSchema(self.schema_file)
            
            self.conversion_checker = ConversionChecker(self.data_parser, summarise, report_unexpected_exception)
            self.extractor = Extractor(self.data_parser)
            
        except Exception as e:
            self._log_error(f"Initialization failed: [{e.__class__.__name__}] {e}")

    # Utility logs tailored to conveter class errors
    def _log_error(self,e,code=exception_messages.UNEXPECTED_EXCEPTION): 
        message = str(e)  # if a simple string message was passed 

        error_obj = {
            "code": code,
            "message": message
        }

        # if not any(existing.get("message") == message for existing in self.error_records):
        self.error_records.append(error_obj)
        return error_obj

    # Convert data against converter schema
    def _convertData(self, expression):
        try:
            fhir_field = expression["fieldNameFHIR"]
            flat_field = expression["fieldNameFlat"]
            expr_type = expression["expression"]["expressionType"]
            expr_rule = expression["expression"]["expressionRule"]

            ### TODO: Remove this after refactoring all fields to be extracted with the Extractor
            values = self.data_parser.get_key_value(fhir_field, flat_field, expr_type, expr_rule)
            ###
            
            if flat_field == "ACTION_FLAG":
                self.converted[flat_field] = self.action_flag
            else:
                for val in values:
                    converted = self.conversion_checker.convertData(expr_type, expr_rule, fhir_field, val)
                    if converted is not None:
                        self.converted[flat_field] = converted
        
        except Exception as e:
            return self._log_error(f"Conversion error [{e.__class__.__name__}]: {e}", code=exception_messages.PARSING_ERROR)


    # run the conversion against the data
    def run_conversion(self):
        try:
            conversions = self.schema_parser.get_conversions()
        except Exception as e:
            return self._log_error(f"Schema get_conversions error [{e.__class__.__name__}]: {e}")

        for conversion in conversions:
            self._convertData(conversion)
        
        # Collect and store any errors from ConversionChecker
        all_errors = self.conversion_checker.get_error_records()
        self.error_records.extend(all_errors)

        # Add CONVERSION_ERRORS as the 35th field
        self.converted["CONVERSION_ERRORS"] = self.conversion_checker.get_error_records() + self.error_records
        return self.converted

    def get_error_records(self):
        return self.error_records