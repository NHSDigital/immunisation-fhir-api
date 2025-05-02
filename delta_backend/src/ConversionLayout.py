
# This file holds the schema/base layout that maps FHIR fields to flat JSON fields
# Each entry tells the converter how to extract and transform a specific value

ConvertLayout = {
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
        "expressionType": "NHSNUMBER",
        "expressionRule": ""
      }
    },
    {
      "fieldNameFHIR": "contained|#:Patient|name|#:official|given|0",
      "fieldNameFlat": "PERSON_FORENAME",
      "expression": {
        "expressionName": "Not Empty",
        "expressionType": "NOTEMPTY",
        "expressionRule": ""
      }
    },
    {
      "fieldNameFHIR": "contained|#:Patient|name|#:official|family",
      "fieldNameFlat": "PERSON_SURNAME",
      "expression": {
        "expressionName": "Not Empty",
        "expressionType": "NOTEMPTY",
        "expressionRule": ""
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
        "expressionType": "GENDER",
        "expressionRule": ""
      }
    },
    {
      "fieldNameFHIR": "contained|#:Patient|address|#:postalCode|postalCode",
      "fieldNameFlat": "PERSON_POSTCODE",
      "expression": {
        "expressionName": "Defaults to",
        "expressionType": "DEFAULT",
        "expressionRule": "ZZ99 3CZ"
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
        "expressionType": "NOTEMPTY",
        "expressionRule": ""
      }
    },
    {
      "fieldNameFHIR": "performer|#:Organization|actor|identifier|system",
      "fieldNameFlat": "SITE_CODE_TYPE_URI",
      "expression": {
        "expressionName": "Defaults to",
        "expressionType": "DEFAULT",
        "expressionRule": "https://fhir.nhs.uk/Id/ods-organization-code"
      }
    },
    {
      "fieldNameFHIR": "identifier|0|value",
      "fieldNameFlat": "UNIQUE_ID",
      "expression": {
        "expressionName": "Not Empty",
        "expressionType": "NOTEMPTY",
        "expressionRule": ""
      }
    },
    {
      "fieldNameFHIR": "identifier|0|system",
      "fieldNameFlat": "UNIQUE_ID_URI",
      "expression": {
        "expressionName": "Not Empty",
        "expressionType": "NOTEMPTY",
        "expressionRule": ""
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
        "expressionType": "NOTEMPTY",
        "expressionRule": ""
      }
    },
    {
      "fieldNameFHIR": "contained|#:Practitioner|name|0|family",
      "fieldNameFlat": "PERFORMING_PROFESSIONAL_SURNAME",
      "expression": {
        "expressionName": "Not Empty",
        "expressionType": "NOTEMPTY",
        "expressionRule": ""
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
        "expressionType": "NOTEMPTY",
        "expressionRule": ""
      }
    },
    {
      "fieldNameFHIR": "extension|0|valueCodeableConcept|coding|0|display",
      "fieldNameFlat": "VACCINATION_PROCEDURE_TERM",
      "expression": {
        "expressionName": "Not Empty",
        "expressionType": "NOTEMPTY",
        "expressionRule": ""
      }
    },
    {
      "fieldNameFHIR": "protocolApplied|0|doseNumberPositiveInt",
      "fieldNameFlat": "DOSE_SEQUENCE",
      "expression": {
        "expressionName": "Not Empty",
        "expressionType": "DOSESEQUENCE",
        "expressionRule": ""
      }
    },
    {
      "fieldNameFHIR": "vaccineCode|coding|#:http://snomed.info/sct|code",
      "fieldNameFlat": "VACCINE_PRODUCT_CODE",
      "expression": {
        "expressionName": "Not Empty",
        "expressionType": "SNOMED",
        "expressionRule": "validate-code"
      }
    },
    {
      "fieldNameFHIR": "vaccineCode|coding|#:http://snomed.info/sct|display",
      "fieldNameFlat": "VACCINE_PRODUCT_TERM",
      "expression": {
        "expressionName": "Not Empty",
        "expressionType": "NOTEMPTY",
        "expressionRule": ""
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
        "expressionType": "NOTEMPTY",
        "expressionRule": ""
      }
    },
    {
      "fieldNameFHIR": "site|coding|#:http://snomed.info/sct|display",
      "fieldNameFlat": "SITE_OF_VACCINATION_TERM",
      "expression": {
        "expressionName": "Look Up",
        "expressionType": "LOOKUP",
        "expressionRule": "site|coding|#:http://snomed.info/sct|code"
      }
    },
    {
      "fieldNameFHIR": "route|coding|#:http://snomed.info/sct|code",
      "fieldNameFlat": "ROUTE_OF_VACCINATION_CODE",
      "expression": {
        "expressionName": "Not Empty",
        "expressionType": "NOTEMPTY",
        "expressionRule": ""
      }
    },
    {
      "fieldNameFHIR": "route|coding|#:http://snomed.info/sct|display",
      "fieldNameFlat": "ROUTE_OF_VACCINATION_TERM",
      "expression": {
        "expressionName": "Look Up",
        "expressionType": "LOOKUP",
        "expressionRule": "route|coding|#:http://snomed.info/sct|code"
      }
    },
    {
      "fieldNameFHIR": "doseQuantity|value",
      "fieldNameFlat": "DOSE_AMOUNT",
      "expression": {
        "expressionName": "Not Empty",
        "expressionType": "DEFAULT",
        "expressionRule": ""
      }
    },
    {
      "fieldNameFHIR": "doseQuantity|code",
      "fieldNameFlat": "DOSE_UNIT_CODE",
      "expression": {
        "expressionName": "Only If",
        "expressionType": "ONLYIF",
        "expressionRule": "doseQuantity|system|http://snomed.info/sct"
      }
    },
    {
      "fieldNameFHIR": "doseQuantity|unit",
      "fieldNameFlat": "DOSE_UNIT_TERM",
      "expression": {
        "expressionName": "Not Empty",
        "expressionType": "NOTEMPTY",
        "expressionRule": ""
      }
    },
    {
      "fieldNameFHIR": "reasonCode|#:http://snomed.info/sct|coding|#:http://snomed.info/sct|code",
      "fieldNameFlat": "INDICATION_CODE",
      "expression": {
        "expressionName": "Not Empty",
        "expressionType": "NOTEMPTY",
        "expressionRule": ""
      }
    },
    {
      "fieldNameFHIR": "location|identifier|value",
      "fieldNameFlat": "LOCATION_CODE",
      "expression": {
        "expressionName": "Defaults to",
        "expressionType": "DEFAULT",
        "expressionRule": "X99999"
      }
    },
    {
      "fieldNameFHIR": "location|identifier|system",
      "fieldNameFlat": "LOCATION_CODE_TYPE_URI",
      "expression": {
        "expressionName": "Defaults to",
        "expressionType": "DEFAULT",
        "expressionRule": "https://fhir.nhs.uk/Id/ods-organization-code"
      }
    }
  ]
}
