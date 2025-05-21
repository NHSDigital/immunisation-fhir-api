# Main validation engine
import exception_messages
from conversion_layout import ConversionLayout
from extractor import Extractor
from common.mappings import ActionFlag

class Converter:

    def __init__(self, fhir_data, action_flag = ActionFlag.UPDATE, report_unexpected_exception=True):
        self.converted = {}
        self.error_records = []
        self.action_flag = action_flag
        self.report_unexpected_exception = report_unexpected_exception
               
        try:
            if not fhir_data:
                raise ValueError("FHIR data is required for initialization.")
        
            self.extractor = Extractor(fhir_data, self.report_unexpected_exception)
            self.conversion_layout = ConversionLayout(self.extractor)           
        except Exception as e:
            if report_unexpected_exception:
                self._log_error(f"Initialization failed: [{e.__class__.__name__}] {e}")
            raise

    def run_conversion(self):
        conversions = self.conversion_layout.get_conversion_layout()
        
        for conversion in conversions:
            self._convert_data(conversion)
        
        self.error_records.extend(self.extractor.get_error_records())

        # Add CONVERSION_ERRORS as the 35th field
        self.converted["CONVERSION_ERRORS"] = self.error_records
        return self.converted

    def _convert_data(self, expression):
        try:
            flat_field = expression["fieldNameFlat"]
            extract_value = expression["expressionRule"]
            
            if flat_field == "ACTION_FLAG":
                self.converted[flat_field] = self.action_flag
            else:
                converted = extract_value()
                if converted is not None:
                    self.converted[flat_field] = converted

        except Exception as e:
            self._log_error(f"Conversion error [{e.__class__.__name__}]: {e}", code=exception_messages.PARSING_ERROR)
            self.converted[flat_field] = ""

    def _log_error(self,e,code=exception_messages.UNEXPECTED_EXCEPTION): 
        error_obj = {
            "code": code,
            "message": str(e)
        }
        
        if self.report_unexpected_exception:
            self.error_records.append(error_obj)
    
    def get_error_records(self):
        return self.error_records