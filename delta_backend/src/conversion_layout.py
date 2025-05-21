from extractor import Extractor
from common.mappings import ConversionFieldName

class ConversionField:
    def __init__(self, field_name_flat: str, expression_rule):
        self.field_name_flat = field_name_flat
        self.expression_rule = expression_rule

class ConversionLayout:
    def __init__(self, extractor: Extractor):        
        self.extractor = extractor
        self.conversion_layout = [
            ConversionField(ConversionFieldName.NHS_NUMBER, extractor.extract_nhs_number),
            ConversionField(ConversionFieldName.PERSON_FORENAME, extractor.extract_person_forename),
            ConversionField(ConversionFieldName.PERSON_SURNAME, extractor.extract_person_surname),
            ConversionField(ConversionFieldName.PERSON_DOB, extractor.extract_person_dob),
            ConversionField(ConversionFieldName.PERSON_GENDER_CODE, extractor.extract_person_gender),
            ConversionField(ConversionFieldName.PERSON_POSTCODE, extractor.extract_valid_address),
            ConversionField(ConversionFieldName.DATE_AND_TIME, extractor.extract_date_time),
            ConversionField(ConversionFieldName.SITE_CODE, extractor.extract_site_code),
            ConversionField(ConversionFieldName.SITE_CODE_TYPE_URI, extractor.extract_site_code_type_uri),
            ConversionField(ConversionFieldName.UNIQUE_ID, extractor.extract_unique_id),
            ConversionField(ConversionFieldName.UNIQUE_ID_URI, extractor.extract_unique_id_uri),
            ConversionField(ConversionFieldName.ACTION_FLAG, ""),
            ConversionField(ConversionFieldName.PERFORMING_PROFESSIONAL_FORENAME, extractor.extract_practitioner_forename),
            ConversionField(ConversionFieldName.PERFORMING_PROFESSIONAL_SURNAME, extractor.extract_practitioner_surname),
            ConversionField(ConversionFieldName.RECORDED_DATE, extractor.extract_recorded_date),
            ConversionField(ConversionFieldName.PRIMARY_SOURCE, extractor.extract_primary_source),
            ConversionField(ConversionFieldName.VACCINATION_PROCEDURE_CODE, extractor.extract_vaccination_procedure_code),
            ConversionField(ConversionFieldName.VACCINATION_PROCEDURE_TERM, extractor.extract_vaccination_procedure_term),
            ConversionField(ConversionFieldName.DOSE_SEQUENCE, extractor.extract_dose_sequence),
            ConversionField(ConversionFieldName.VACCINE_PRODUCT_CODE, extractor.extract_vaccine_product_code),
            ConversionField(ConversionFieldName.VACCINE_PRODUCT_TERM, extractor.extract_vaccine_product_term),
            ConversionField(ConversionFieldName.VACCINE_MANUFACTURER, extractor.extract_vaccine_manufacturer),
            ConversionField(ConversionFieldName.BATCH_NUMBER, extractor.extract_batch_number),
            ConversionField(ConversionFieldName.EXPIRY_DATE, extractor.extract_expiry_date),
            ConversionField(ConversionFieldName.SITE_OF_VACCINATION_CODE, extractor.extract_site_of_vaccination_code),
            ConversionField(ConversionFieldName.SITE_OF_VACCINATION_TERM, extractor.extract_site_of_vaccination_term),
            ConversionField(ConversionFieldName.ROUTE_OF_VACCINATION_CODE, extractor.extract_route_of_vaccination_code),
            ConversionField(ConversionFieldName.ROUTE_OF_VACCINATION_TERM, extractor.extract_route_of_vaccination_term),
            ConversionField(ConversionFieldName.DOSE_AMOUNT, extractor.extract_dose_amount),
            ConversionField(ConversionFieldName.DOSE_UNIT_CODE, extractor.extract_dose_unit_code),
            ConversionField(ConversionFieldName.DOSE_UNIT_TERM, extractor.extract_dose_unit_term),
            ConversionField(ConversionFieldName.INDICATION_CODE, extractor.extract_indication_code),
            ConversionField(ConversionFieldName.LOCATION_CODE, extractor.extract_location_code),
            ConversionField(ConversionFieldName.LOCATION_CODE_TYPE_URI, extractor.extract_location_code_type_uri),
        ]

    def get_conversion_layout(self):
        return self.conversion_layout
