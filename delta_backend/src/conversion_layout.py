from extractor import Extractor

class ConversionLayout:
    def __init__(self, extractor: Extractor):        
        self.extractor = extractor
        self.conversion_layout = [
          {
              "fieldNameFlat": "NHS_NUMBER",
              "expressionRule": self.extractor.extract_nhs_number
          },
          {
              "fieldNameFlat": "PERSON_FORENAME",
              "expressionRule": self.extractor.extract_person_forename
          },
          {
              "fieldNameFlat": "PERSON_SURNAME",
              "expressionRule": self.extractor.extract_person_surname
          },
          {
              "fieldNameFlat": "PERSON_DOB",
              "expressionRule": self.extractor.extract_person_dob
          },
          {
              "fieldNameFlat": "PERSON_GENDER_CODE",
              "expressionRule": self.extractor.extract_person_gender
          },
          {
              "fieldNameFlat": "PERSON_POSTCODE",
              "expressionRule": self.extractor.extract_valid_address
          },
          {
              "fieldNameFlat": "DATE_AND_TIME",
              "expressionRule": self.extractor.extract_date_time
          },
          {
              "fieldNameFlat": "SITE_CODE",
              "expressionRule": self.extractor.extract_site_code
          },
          {
              "fieldNameFlat": "SITE_CODE_TYPE_URI",
              "expressionRule": self.extractor.extract_site_code_type_uri
          },
          {
              "fieldNameFlat": "UNIQUE_ID",
              "expressionRule": self.extractor.extract_unique_id
          },
          {
              "fieldNameFlat": "UNIQUE_ID_URI",
              "expressionRule": self.extractor.extract_unique_id_uri
          },
          {
              "fieldNameFlat": "ACTION_FLAG",
              "expressionRule": ""
          },
          {
              "fieldNameFlat": "PERFORMING_PROFESSIONAL_FORENAME",
              "expressionRule": self.extractor.extract_practitioner_forename
          },
          {
              "fieldNameFlat": "PERFORMING_PROFESSIONAL_SURNAME",
              "expressionRule": self.extractor.extract_practitioner_surname
          },
          {
              "fieldNameFlat": "RECORDED_DATE",
              "expressionRule": self.extractor.extract_recorded_date
          },
          {
              "fieldNameFlat": "PRIMARY_SOURCE",
              "expressionRule": self.extractor.extract_primary_source
          },
          {
              "fieldNameFlat": "VACCINATION_PROCEDURE_CODE",
              "expressionRule": self.extractor.extract_vaccination_procedure_code
          },
          {
              "fieldNameFlat": "VACCINATION_PROCEDURE_TERM",
              "expressionRule": self.extractor.extract_vaccination_procedure_term
          },
          {
              "fieldNameFlat": "DOSE_SEQUENCE",
              "expressionRule": self.extractor.extract_dose_sequence
          },
          {
              "fieldNameFlat": "VACCINE_PRODUCT_CODE",
              "expressionRule": self.extractor.extract_vaccine_product_code
          },
          {
              "fieldNameFlat": "VACCINE_PRODUCT_TERM",
              "expressionRule": self.extractor.extract_vaccine_product_term
          },
          {
              "fieldNameFlat": "VACCINE_MANUFACTURER",
              "expressionRule": self.extractor.extract_vaccine_manufacturer
          },
          {
              "fieldNameFlat": "BATCH_NUMBER",
              "expressionRule": self.extractor.extract_batch_number
          },
          {
              "fieldNameFlat": "EXPIRY_DATE",
              "expressionRule": self.extractor.extract_expiry_date
          },
          {
              "fieldNameFlat": "SITE_OF_VACCINATION_CODE",
              "expressionRule": self.extractor.extract_site_of_vaccination_code
          },
          {
              "fieldNameFlat": "SITE_OF_VACCINATION_TERM",
              "expressionRule": self.extractor.extract_site_of_vaccination_term
          },
          {
              "fieldNameFlat": "ROUTE_OF_VACCINATION_CODE",
              "expressionRule": self.extractor.extract_route_of_vaccination_code
          },
          {
              "fieldNameFlat": "ROUTE_OF_VACCINATION_TERM",
              "expressionRule": self.extractor.extract_route_of_vaccination_term
          },
          {
              "fieldNameFlat": "DOSE_AMOUNT",
              "expressionRule": self.extractor.extract_dose_amount
          },
          {
              "fieldNameFlat": "DOSE_UNIT_CODE",
              "expressionRule": self.extractor.extract_dose_unit_code
          },
          {
              "fieldNameFlat": "DOSE_UNIT_TERM",
              "expressionRule": self.extractor.extract_dose_unit_term
          },
          {
              "fieldNameFlat": "INDICATION_CODE",
              "expressionRule": self.extractor.extract_indication_code
          },
          {
              "fieldNameFlat": "LOCATION_CODE",
              "expressionRule": self.extractor.extract_location_code
          },
          {
              "fieldNameFlat": "LOCATION_CODE_TYPE_URI",
              "expressionRule": self.extractor.extract_location_code_type_uri
          }
        ]

    def get_conversion_layout(self):
        return self.conversion_layout