# Main validation engine
import exception_messages
from conversion_layout import ConversionField, ConversionLayout
from extractor import Extractor
from mappings import ActionFlag


class Converter:
    def __init__(self, fhir_data, action_flag=ActionFlag.UPDATE):
        self.converted = {}
        self.error_records = []
        self.action_flag = action_flag

        if not fhir_data:
            raise ValueError("FHIR data is required for initialization.")

        self.extractor = Extractor(fhir_data)
        self.conversion_layout = ConversionLayout(self.extractor)

    def run_conversion(self):
        for conversion in self.conversion_layout.get_conversion_layout():
            self._convert_data(conversion)

        self.error_records.extend(self.extractor.get_error_records())

        # Add CONVERSION_ERRORS as the 35th field
        self.converted["CONVERSION_ERRORS"] = self.error_records
        return self.converted

    def _convert_data(self, conversion: ConversionField):
        flat_field = conversion.field_name_flat

        try:
            if flat_field == "ACTION_FLAG":
                self.converted[flat_field] = self.action_flag
                return

            if (converted := conversion.expression_rule()) is not None:
                self.converted[flat_field] = converted
        except Exception as error:
            self._log_error(
                flat_field,
                f"Conversion error [{error.__class__.__name__}]: {error}",
                code=exception_messages.PARSING_ERROR,
            )
            self.converted[flat_field] = ""

    def _log_error(self, field_name, e, code):
        self.error_records.append(
            {
                "code": code,
                "field": field_name,
                "value": None,
                "message": str(e),
            }
        )

    def get_error_records(self):
        return self.error_records
