from json_field_extractor import Extractor

class ConversionLayout:
    def __init__(self, fhir_data):
           
        self.extractor = Extractor(fhir_data)
      
        self.conversion_layout = {
          "id": "7d78e9a6-d859-45d3-bb05-df9c405acbdb",
          "schemaName": "JSON Base",
          "version": 1.0,
          "releaseDate": "2024-07-17T00:00:00|000Z",
          "conversions": [
            {
              "fieldNameFHIR": "contained|#:Patient|identifier|#:https://fhir.nhs.uk/Id/nhs-number|value",
              "fieldNameFlat": "NHS_NUMBER",
              "expression": {
                "expressionName": "NHS NUMBER",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_nhs_number
              }
            },
            {
              "fieldNameFHIR": "contained|#:Patient|name|#:official|given|0",
              "fieldNameFlat": "PERSON_FORENAME",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_person_forename
              }
            },
            {
              "fieldNameFHIR": "contained|#:Patient|name|#:official|family",
              "fieldNameFlat": "PERSON_SURNAME",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_person_surname
              }
            },
            {
              "fieldNameFHIR": "contained|#:Patient|birthDate",
              "fieldNameFlat": "PERSON_DOB",
              "expression": {
                "expressionName": "Date Convert",
                "expressionType": "DATECONVERT",
                "expressionRule": "%Y%m%d"
              }
            },
            {
              "fieldNameFHIR": "contained|#:Patient|gender",
              "fieldNameFlat": "PERSON_GENDER_CODE",
              "expression": {
                "expressionName": "Gender Conversion",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_person_gender
              }
            },
            {
              "fieldNameFHIR": "contained|#:Patient|address|#:postalCode|postalCode",
              "fieldNameFlat": "PERSON_POSTCODE",
              "expression": {
                "expressionName": "Defaults to",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_valid_address
              }
            },
            {
              "fieldNameFHIR": "occurrenceDateTime",
              "fieldNameFlat": "DATE_AND_TIME",
              "expression": {
                "expressionName": "Date Convert",
                "expressionType": "DATETIME",
                "expressionRule": "fhir-date"
              }
            },
            {
              "fieldNameFHIR": "performer|#:Organization|actor|identifier|value",
              "fieldNameFlat": "SITE_CODE",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_site_code
              }
            },
            {
              "fieldNameFHIR": "performer|#:Organization|actor|identifier|system",
              "fieldNameFlat": "SITE_CODE_TYPE_URI",
              "expression": {
                "expressionName": "Defaults to",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_site_code_type_uri
              }
            },
            {
              "fieldNameFHIR": "identifier|0|value",
              "fieldNameFlat": "UNIQUE_ID",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_unique_id
              }
            },
            {
              "fieldNameFHIR": "identifier|0|system",
              "fieldNameFlat": "UNIQUE_ID_URI",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_unique_id_uri
              }
            },
            {
              "fieldNameFHIR": "id",
              "fieldNameFlat": "ACTION_FLAG",
              "expression": {
                "expressionName": "Change To",
                "expressionType": "CHANGETO",
                "expressionRule": "update"
              }
            },
            {
              "fieldNameFHIR": "contained|#:Practitioner|name|0|given|0",
              "fieldNameFlat": "PERFORMING_PROFESSIONAL_FORENAME",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_practitioner_forename
              }
            },
            {
              "fieldNameFHIR": "contained|#:Practitioner|name|0|family",
              "fieldNameFlat": "PERFORMING_PROFESSIONAL_SURNAME",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_practitioner_surname
              }
            },
            {
              "fieldNameFHIR": "recorded",
              "fieldNameFlat": "RECORDED_DATE",
              "expression": {
                "expressionName": "Date Convert",
                "expressionType": "DATECONVERT",
                "expressionRule": "%Y%m%d"
              }
            },
            {
              "fieldNameFHIR": "primarySource",
              "fieldNameFlat": "PRIMARY_SOURCE",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "BOOLEAN",
                "expressionRule": ""
              }
            },
            {
              "fieldNameFHIR": "extension|#:https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure|valueCodeableConcept|coding|#:http://snomed.info/sct|code",
              "fieldNameFlat": "VACCINATION_PROCEDURE_CODE",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_vaccination_procedure_code
              }
            },
            {
              "fieldNameFHIR": "extension|0|valueCodeableConcept|coding|0|display",
              "fieldNameFlat": "VACCINATION_PROCEDURE_TERM",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_vaccination_procedure_term
              }
            },
            {
              "fieldNameFHIR": "protocolApplied|0|doseNumberPositiveInt",
              "fieldNameFlat": "DOSE_SEQUENCE",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_dose_sequence
              }
            },
            {
              "fieldNameFHIR": "vaccineCode|coding|#:http://snomed.info/sct|code",
              "fieldNameFlat": "VACCINE_PRODUCT_CODE",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_vaccine_product_code
              }
            },
            {
              "fieldNameFHIR": "vaccineCode|coding|#:http://snomed.info/sct|display",
              "fieldNameFlat": "VACCINE_PRODUCT_TERM",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_vaccine_product_term
              }
            },
            {
              "fieldNameFHIR": "manufacturer|display",
              "fieldNameFlat": "VACCINE_MANUFACTURER",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NOTEMPTY",
                "expressionRule": ""
              }
            },
            {
              "fieldNameFHIR": "lotNumber",
              "fieldNameFlat": "BATCH_NUMBER",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NOTEMPTY",
                "expressionRule": ""
              }
            },
            {
              "fieldNameFHIR": "expirationDate",
              "fieldNameFlat": "EXPIRY_DATE",
              "expression": {
                "expressionName": "Date Convert",
                "expressionType": "DATECONVERT",
                "expressionRule": "%Y%m%d"
              }
            },
            {
              "fieldNameFHIR": "site|coding|#:http://snomed.info/sct|code",
              "fieldNameFlat": "SITE_OF_VACCINATION_CODE",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_site_of_vaccination_code
              }
            },
            {
              "fieldNameFHIR": "site|coding|#:http://snomed.info/sct|display",
              "fieldNameFlat": "SITE_OF_VACCINATION_TERM",
              "expression": {
                "expressionName": "Look Up",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_site_of_vaccination_term
              }
            },
            {
              "fieldNameFHIR": "route|coding|#:http://snomed.info/sct|code",
              "fieldNameFlat": "ROUTE_OF_VACCINATION_CODE",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_route_of_vaccination_code
              }
            },
            {
              "fieldNameFHIR": "route|coding|#:http://snomed.info/sct|display",
              "fieldNameFlat": "ROUTE_OF_VACCINATION_TERM",
              "expression": {
                "expressionName": "Look Up",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_route_of_vaccination_term
              }
            },
            {
              "fieldNameFHIR": "doseQuantity|value",
              "fieldNameFlat": "DOSE_AMOUNT",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_dose_amount
              }
            },
            {
              "fieldNameFHIR": "doseQuantity|code",
              "fieldNameFlat": "DOSE_UNIT_CODE",
              "expression": {
                "expressionName": "Only If",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_dose_unit_code
              }
            },
            {
              "fieldNameFHIR": "doseQuantity|unit",
              "fieldNameFlat": "DOSE_UNIT_TERM",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_dose_unit_term
              }
            },
            {
              "fieldNameFHIR": "reasonCode|#:http://snomed.info/sct|coding|#:http://snomed.info/sct|code",
              "fieldNameFlat": "INDICATION_CODE",
              "expression": {
                "expressionName": "Not Empty",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_indication_code
              }
            },
            {
              "fieldNameFHIR": "location|identifier|value",
              "fieldNameFlat": "LOCATION_CODE",
              "expression": {
                "expressionName": "Defaults to",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_location_code
              }
            },
            {
              "fieldNameFHIR": "location|identifier|system",
              "fieldNameFlat": "LOCATION_CODE_TYPE_URI",
              "expression": {
                "expressionName": "Defaults to",
                "expressionType": "NORMAL",
                "expressionRule": self.extractor.extract_location_code_type_uri
              }
            }
          ]
        }

    def get_conversion_layout(self):
        return self.conversion_layout