ERROR_MAP = {
    "Common_field": {
        "resourceType": "OperationOutcome",
        "profile": "https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome",
        "system": "https://fhir.nhs.uk/Codesystem/http-error-codes",
        "severity": "error",
    },
    "invalid_DateFrom_Include": {        
        "code": "INVALID",
        "diagnostics": "Search parameter -date.from must be in format: YYYY-MM-DD; Search parameter _include may only be 'Immunization:patient' if provided."
    },
    "invalid_NHSNumber": {        
        "code": "INVALID",
        "diagnostics": "Search parameter patient.identifier must be a valid NHS number."
    },
    "empty_NHSNumber": {        
        "code": "INVALID",
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value must be a non-empty string"
    },
    "invalid_include": {        
        "code": "INVALID",
        "diagnostics": "Search parameter _include may only be 'Immunization:patient' if provided."
    },
    "invalid_DateFrom_To": {        
        "code": "INVALID",
        "diagnostics": "Search parameter -date.from must be in format: YYYY-MM-DD; Search parameter -date.to must be in format: YYYY-MM-DD"
    },
    "invalid_DateFrom_DateTo_Include": {        
        "code": "INVALID",
        "diagnostics": "Search parameter -date.from must be in format: YYYY-MM-DD; Search parameter -date.to must be in format: YYYY-MM-DD; Search parameter _include may only be 'Immunization:patient' if provided."
    },
    "invalid_DiseaseType": {
        "code": "INVALID",
         "diagnostics": "-immunization.target must be one or more of the following: ROTAVIRUS, RSV, SHINGLES, 6IN1, MMR, FLU, 3IN1, PERTUSSIS, MENB, HIB, MMRV, BCG, MENACWY, 4IN1, COVID, PNEUMOCOCCAL, HPV, HEPB"
    },
    "invalid_DateFrom": {
        "code": "INVALID",
        "diagnostics": "Search parameter -date.from must be in format: YYYY-MM-DD"
    }, 
    "invalid_DateTo": {
        "code": "INVALID",
        "diagnostics": "Search parameter -date.to must be in format: YYYY-MM-DD"
    },  
    "unauthorized_access": {
        "code": "FORBIDDEN",
        "diagnostics": "Unauthorized request for vaccine type"
    },  
    "not_found": {
        "code": "NOT-FOUND",
        "diagnostics": f"Immunization resource does not exist. ID: <imms_id>"
    },      
    "forbidden": {
        "code": "FORBIDDEN",
        "diagnostics": f"Unauthorized request for vaccine type"
    },
    "doseNumberPositiveInt_PositiveInteger": {
        "code": "INVARIANT",
        "diagnostics": "Validation errors: protocolApplied[0].doseNumberPositiveInt must be a positive integer"
    },
    "doseNumberPositiveInt_ValidRange": {
        "code": "INVARIANT",
        "diagnostics": "Validation errors: protocolApplied[0].doseNumberPositiveInt must be an integer in the range 1 to 9"
    },
    "invalid_OccurrenceDateTime": {
        "code": "INVARIANT",
        "diagnostics": "Validation errors: occurrenceDateTime must be a valid datetime in one of the following formats:- 'YYYY-MM-DD' — Full date only- 'YYYY-MM-DDThh:mm:ss%z' — Full date and time with timezone (e.g. +00:00 or +01:00)- 'YYYY-MM-DDThh:mm:ss.f%z' — Full date and time with milliseconds and timezone- Date must not be in the future.Only '+00:00' and '+01:00' are accepted as valid timezone offsets. Note that partial dates are not allowed for occurrenceDateTime in this service."
    },
    "empty_OccurrenceDateTime": {
        "code": "INVARIANT",
        "diagnostics": "1 validation error for Immunization __root__ Expect any of field value from this list ['occurrenceDateTime', 'occurrenceString']. (type=value_error)"
    },
    "invalid_recorded": {
        "code": "INVARIANT",
        "diagnostics": "Validation errors: recorded must be a valid datetime in one of the following formats:- 'YYYY-MM-DD' — Full date only- 'YYYY-MM-DDThh:mm:ss%z' — Full date and time with timezone (e.g. +00:00 or +01:00)- 'YYYY-MM-DDThh:mm:ss.f%z' — Full date and time with milliseconds and timezone- Date must not be in the future."
    },
    "empty_recorded": {
        "code": "INVARIANT",
        "diagnostics": "Validation errors: recorded is a mandatory field"
    },
    "future_DateOfBirth": {
        "code": "INVARIANT",
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].birthDate must not be in the future"
    },
    "missing_DateOfBirth": {
        "code": "INVARIANT",
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].birthDate is a mandatory field"
    },
    "invalid_DateOfBirth": {
        "code": "INVARIANT",
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].birthDate must be a valid date string in the format \"YYYY-MM-DD\""
    },
    "invalid_expirationDate": {
        "code": "INVARIANT",
        "diagnostics": 'Validation errors: expirationDate must be a valid date string in the format \"YYYY-MM-DD\"'
    },
    "invalid_nhsnumber_length" : {
        "code": "INVARIANT",
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value must be 10 characters"
    },
    "no_forename" : {
        "code": "INVARIANT",
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].name[0].given is a mandatory field"
    },
    "empty_forename" : {
        "code": "INVARIANT",
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].name[0].given must be an array"
    },
    "empty_array_item_forename" : {
        "code": "INVARIANT",
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].name[0].given[0] must be a non-empty string"
    },
    "no_surname" : {
        "code": "INVARIANT",
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].name[0].family is a mandatory field"
    },
    "empty_forename_surname" : {
        "code": "INVARIANT",
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].name[0].given is a mandatory field; contained[?(@.resourceType=='Patient')].name[0].family is a mandatory field"
    },
    "empty_surname" : {
        "code": "INVARIANT",
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].name[0].family must be a non-empty string"
    },
    "invalid_gender" : {
        "code": "INVARIANT",
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].gender must be one of the following: male, female, other, unknown"
    },
    "empty_gender" :{
        "code": "INVARIANT",
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].gender must be a non-empty string"
    },
    "missing_gender" :{
        "code": "INVARIANT",
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].gender is a mandatory field"
    },
     "invalid_mod11_nhsnumber" :{
        "code": "INVARIANT",
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].identifier[0].value is not a valid NHS number"
    },
     "should_be_string" :{
        "code": "INVARIANT",
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].gender must be a string"
    },
     "max_len_surname":{
        "code": "INVARIANT",
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].name[0].family must be 35 or fewer characters"
    },
    "max_len_forename":{
        "code": "INVARIANT",            
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].name[0].given[0] must be 35 or fewer characters"
    },
    "max_item_forename":{
        "code": "INVARIANT",            
        "diagnostics": "Validation errors: contained[?(@.resourceType=='Patient')].name[0].given must be an array of maximum length 5"
    },
    "empty_site_code": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: performer[?(@.actor.type=='Organization')].actor.identifier.value is a mandatory field"
    },
    "no_site_code": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: performer[?(@.actor.type=='Organization')].actor.identifier.value must be a non-empty string"
    },
    "empty_site_code_uri": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: performer[?(@.actor.type=='Organization')].actor.identifier.system is a mandatory field"
    },
    "no_site_code_uri": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: performer[?(@.actor.type=='Organization')].actor.identifier.system must be a non-empty string"
    },
     "empty_location_code": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: location.identifier.value is a mandatory field"
    },
    "no_location_code": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: location.identifier.value must be a non-empty string"
    },
    "empty_location_code_uri": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: location.identifier.system is a mandatory field"
    },
    "no_location_code_uri": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: location.identifier.system must be a non-empty string"
    },
    "no_unique_identifiers": {
        "code": "INVARIANT",    
        "diagnostics": "UNIQUE_ID or UNIQUE_ID_URI is missing"
    },
    "no_unique_id":{
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: identifier[0].value must be a non-empty string"
    },
    "no_unique_id_uri":{
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: identifier[0].system must be a non-empty string"
    },
    "empty_primary_source": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: primarySource is a mandatory field"
    },
    "no_primary_source": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: primarySource must be a boolean"
    },
    "no_procedure_code": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].code is a mandatory field"
    },
    "empty_procedure_code": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].code must be a non-empty string"
    },
    "empty_product_term": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: vaccineCode.coding[?(@.system=='http://snomed.info/sct')].display must be a non-empty string"
    },
    "empty_product_code": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: vaccineCode.coding[?(@.system=='http://snomed.info/sct')].code must be a non-empty string"
    },
    "empty_procedure_term": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: extension[?(@.url=='https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure')].valueCodeableConcept.coding[?(@.system=='http://snomed.info/sct')].display must be a non-empty string"
    },
    "invalid_action_flag": {
        "code": "INVARIANT",
        "diagnostics": "Invalid ACTION_FLAG - ACTION_FLAG must be 'NEW', 'UPDATE' or 'DELETE'"
    },
    "empty_manufacturer": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: manufacturer.display must be a non-empty string"
    },
    "empty_lot_number": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: lotNumber must be a non-empty string"
    },
    "empty_vaccine_site_code": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: site.coding[?(@.system=='http://snomed.info/sct')].code must be a non-empty string"
    },
    "empty_vaccine_site_term": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: site.coding[?(@.system=='http://snomed.info/sct')].display must be a non-empty string"
    },
    "empty_route_code": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: route.coding[?(@.system=='http://snomed.info/sct')].code must be a non-empty string"
    },
    "empty_route_term": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: route.coding[?(@.system=='http://snomed.info/sct')].display must be a non-empty string"
    },
    "empty_doseQuantity_code": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: doseQuantity.code must be a non-empty string"
    },
    "empty_doseQuantity_term": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: doseQuantity.unit must be a non-empty string"
    },
    "empty_indication_code": {
        "code": "INVARIANT",    
        "diagnostics": "Validation errors: reasonCode[0].coding[0].code must be a non-empty string"
    },
    "invalid_etag": {
        "code": "INVARIANT",  
        "diagnostics": "Validation errors: Immunization resource version:<version> in the request headers is invalid."
    }
}
