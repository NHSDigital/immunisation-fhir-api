@Create_Feature @functional
Feature: Create the immunization event for a patient

@Delete_cleanUp @smoke
Scenario Outline:  Verify that the POST Create API for different vaccine types
    Given Valid token is generated for the '<Supplier>'
    And Valid json payload is created with Patient '<Patient>' and vaccine_type '<vaccine_type>'
    When Trigger the post create request
    Then The request will be successful with the status code '201'
    And The location key and Etag in header will contain the Immunization Id and version
    And The X-Request-ID and X-Correlation-ID keys in header will populate correctly
    And The imms event table will be populated with the correct data for 'created' event
    And The delta table will be populated with the correct data for created event

    Examples: 
      | Patient  | vaccine_type| Supplier     |
      |Random    | COVID       | Postman_Auth |
      |Random    | RSV         | RAVS         |
      |Random    | FLU         | MAVIS        |
      |Random    | MMR         | Postman_Auth |
      |Random    | MENACWY     | TPP          |
      |Random    | 3IN1        | TPP          |
      |Random    | MMRV        | EMIS         |
      |Random    | PERTUSSIS   | EMIS         |
      |Random    | SHINGLES    | EMIS         |
      |Random    | PNEUMOCOCCAL| EMIS         |
      |Random    | 4IN1        | TPP          |
      |Random    | 6IN1        | EMIS         |
      |Random    | HIB         | TPP          |
      |Random    | MENB        | TPP          |
      |Random    | ROTAVIRUS   | MEDICUS      |
      |Random    | HEPB        | EMIS         |
      |Random    | BCG         | MEDICUS      |

@Delete_cleanUp @vaccine_type_6IN1 @patient_id_Random @supplier_name_EMIS
Scenario: Verify that VACCINATION_PROCEDURE_TERM, VACCINE_PRODUCT_TERM, SITE_OF_VACCINATION_TERM, ROUTE_OF_VACCINATION_TERM fields are mapped to respective text fields in imms delta table
    Given Valid json payload is created where vaccination terms has text field populated
    When Trigger the post create request
    Then The request will be successful with the status code '201'
    And The location key and Etag in header will contain the Immunization Id and version
    And The terms are mapped to the respective text fields in imms delta table

@Delete_cleanUp @vaccine_type_BCG @patient_id_Random @supplier_name_EMIS
Scenario: Verify that VACCINATION_PROCEDURE_TERM, VACCINE_PRODUCT_TERM fields are mapped to first instance of coding.display fields in imms delta table
    Given Valid json payload is created where vaccination terms has multiple instances of coding
    When Trigger the post create request
    Then The request will be successful with the status code '201'
    And The location key and Etag in header will contain the Immunization Id and version
    And The terms are mapped to first instance of coding.display fields in imms delta table

@Delete_cleanUp @vaccine_type_HEPB @patient_id_Random @supplier_name_MEDICUS
Scenario: Verify that VACCINATION_PROCEDURE_TERM, VACCINE_PRODUCT_TERM, SITE_OF_VACCINATION_TERM, ROUTE_OF_VACCINATION_TERM fields are mapped to correct instance of coding.display fields in imms delta table
    Given Valid json payload is created where vaccination terms has multiple instance of coding with different coding system
    When Trigger the post create request
    Then The request will be successful with the status code '201'
    And The location key and Etag in header will contain the Immunization Id and version
    And The terms are mapped to correct instance of coding.display fields in imms delta table

@Delete_cleanUp @vaccine_type_PERTUSSIS @patient_id_Random @supplier_name_EMIS
Scenario: Verify that VACCINATION_PROCEDURE_TERM, VACCINE_PRODUCT_TERM, SITE_OF_VACCINATION_TERM, ROUTE_OF_VACCINATION_TERM fields are mapped to coding.display in imms delta table in case of only one instance of coding
    Given Valid json payload is created where vaccination terms has one instance of coding with no text or value string field
    When Trigger the post create request
    Then The request will be successful with the status code '201'
    And The location key and Etag in header will contain the Immunization Id and version
    And The terms are mapped to correct coding.display fields in imms delta table

@Delete_cleanUp @vaccine_type_HIB @patient_id_Random @supplier_name_TPP
Scenario: Verify that VACCINATION_PROCEDURE_TERM, VACCINE_PRODUCT_TERM, SITE_OF_VACCINATION_TERM, ROUTE_OF_VACCINATION_TERM fields are blank in imms delta table if no text or value string or display field is present
    Given Valid json payload is created where vaccination terms has no text or value string or display field
    When Trigger the post create request
    Then The request will be successful with the status code '201'
    And The location key and Etag in header will contain the Immunization Id and version
    And The terms are blank in imms delta table 

Scenario Outline:  Verify that the POST Create API for different supplier fails on access denied
    Given Valid token is generated for the '<Supplier>'
    And Valid json payload is created with Patient '<Patient>' and vaccine_type '<vaccine_type>'
    When Trigger the post create request
    Then The request will be unsuccessful with the status code '403'
    And The Response JSONs should contain correct error message for 'unauthorized_access' access
    Examples: 
      | Patient  | vaccine_type| Supplier     |
      |Random    | COVID       | MAVIS        |
      |Random    | RSV         | MAVIS        |
      |Random    | RSV         | SONAR        |

@Delete_cleanUp @supplier_name_Postman_Auth @vaccine_type_RSV @patient_id_Mod11_NHS
Scenario:  Verify that the POST Create API for invalid but Mod11 compliant NHS Number 
    Given Valid json payload is created
    When Trigger the post create request
    Then The request will be successful with the status code '201'
    And The location key and Etag in header will contain the Immunization Id and version
    And The X-Request-ID and X-Correlation-ID keys in header will populate correctly
    And The imms event table will be populated with the correct data for 'created' event
    And The delta table will be populated with the correct data for created event

@supplier_name_Postman_Auth @vaccine_type_RSV @patient_id_Random
Scenario Outline:  Verify that the POST Create API will fail if doseNumberPositiveInt is not valid
    Given Valid json payload is created where doseNumberPositiveInt is '<doseNumberPositiveInt>'
    When Trigger the post create request
    Then The request will be unsuccessful with the status code '400'
    And The Response JSONs should contain correct error message for '<error_type>'
    Examples: 
      | doseNumberPositiveInt | error_type                                  |
      | -1                    | doseNumberPositiveInt_PositiveInteger       |
      | 0                     | doseNumberPositiveInt_PositiveInteger       |
      | 10                    | doseNumberPositiveInt_ValidRange            |


@Delete_cleanUp @supplier_name_Postman_Auth @vaccine_type_RSV @patient_id_Random
Scenario: Verify that the POST Create API will be successful if all date field has valid past date
    Given Valid json payload is created where date fields has past date
    When Trigger the post create request
    Then The request will be successful with the status code '201'
    And The location key and Etag in header will contain the Immunization Id and version


@supplier_name_Postman_Auth @vaccine_type_RSV @patient_id_Random
Scenario Outline: Verify that the POST Create API will fail if occurrenceDateTime has future or invalid formatted date
    Given Valid json payload is created where occurrenceDateTime has invalid '<Date>' date
    When Trigger the post create request
    Then The request will be unsuccessful with the status code '400'
    And The Response JSONs should contain correct error message for '<error_type>'
     Examples: 
        | Date                  | error_type                 |
        | future_occurrence     | invalid_OccurrenceDateTime |
        | invalid_format        | invalid_OccurrenceDateTime |
        | nonexistent           | invalid_OccurrenceDateTime |
        | empty                 | invalid_OccurrenceDateTime |
        | none                  | empty_OccurrenceDateTime   |

@supplier_name_Postman_Auth @vaccine_type_RSV @patient_id_Random
Scenario Outline: Verify that the POST Create API will fail if recorded has future or invalid formatted date
    Given Valid json payload is created where recorded has invalid '<Date>' date
    When Trigger the post create request
    Then The request will be unsuccessful with the status code '400'
    And The Response JSONs should contain correct error message for '<error_type>'
     Examples: 
        | Date                  | error_type       |
        | future_date           | invalid_recorded |
        | invalid_format        | invalid_recorded |
        | nonexistent           | invalid_recorded |
        | empty                 | invalid_recorded |
        | none                  | empty_recorded   |

@supplier_name_Postman_Auth @vaccine_type_RSV @patient_id_Random
Scenario Outline: Verify that the POST Create API will fail if patient's data of birth has future or invalid formatted date
    Given Valid json payload is created where date of birth has invalid '<Date>' date
    When Trigger the post create request
    Then The request will be unsuccessful with the status code '400'
    And The Response JSONs should contain correct error message for '<error_type>'
     Examples: 
        | Date                  | error_type            |   
        | future_date           | future_DateOfBirth    |
        | invalid_format        | invalid_DateOfBirth   |
        | nonexistent           | invalid_DateOfBirth   |
        | empty                 | invalid_DateOfBirth   |
        | none                  | missing_DateOfBirth   |

@supplier_name_Postman_Auth @vaccine_type_RSV @patient_id_Random
Scenario Outline: Verify that the POST Create API will fail if expiration date has invalid formatted date
    Given Valid json payload is created where expiration date has invalid '<Date>' date
    When Trigger the post create request
    Then The request will be unsuccessful with the status code '400'
    And The Response JSONs should contain correct error message for 'invalid_expirationDate'
     Examples: 
        | Date                  | 
        | invalid_format        |
        | nonexistent           |
        | empty                 |

@supplier_name_Postman_Auth @vaccine_type_RSV @patient_id_Random
Scenario Outline: Verify that the POST Create API will fail if nhs number is invalid
    Given Valid json payload is created where Nhs number is invalid '<invalid_NhsNumber>' 
    When Trigger the post create request
    Then The request will be unsuccessful with the status code '400'
    And The Response JSONs should contain correct error message for '<error_type>'
    Examples: 
    |invalid_NhsNumber  |error_type                 |
    |1234567890         |invalid_mod11_nhsnumber    |
    |12345678           |invalid_nhsnumber_length   |

@supplier_name_Postman_Auth @vaccine_type_RSV @patient_id_Random
Scenario Outline: Verify that the POST Create API will fail if patient forename is invalid  
    Given Valid json payload is created where patient forename is '<forename>'
    When Trigger the post create request
    Then The request will be unsuccessful with the status code '400'
    And The Response JSONs should contain correct error message for '<error_type>'
    Examples:
    | forename              | error_type        |
    | empty                 | empty_forename    |
    | missing               | no_forename       |
    | white_space_array     | empty_forename    |
    | single_value_max_len  | max_len_forename  |
    | max_len_array         | max_item_forename |

@supplier_name_Postman_Auth @vaccine_type_RSV @patient_id_Random
Scenario Outline: Verify that the POST Create API will fail if patient surname is invalid  
    Given Valid json payload is created where patient surname is '<surname>'
    When Trigger the post create request
    Then The request will be unsuccessful with the status code '400'
    And The Response JSONs should contain correct error message for '<error_type>'
    Examples:
    | surname        | error_type      |
    | empty          | empty_surname   |
    | missing        | no_surname      |
    | white_space    | empty_surname   |
    | name_length_36 | max_len_surname |

@supplier_name_Postman_Auth @vaccine_type_RSV @patient_id_Random
Scenario: Verify that the POST Create API will fail if patient name is empty
    Given Valid json payload is created where patient name is empty
    When Trigger the post create request
    Then The request will be unsuccessful with the status code '400'
    And The Response JSONs should contain correct error message for 'empty_forename_surname'

@supplier_name_Postman_Auth @vaccine_type_RSV @patient_id_Random
Scenario Outline: Verify that the POST Create API will fail if patient gender is invalid  
    Given Valid json payload is created where patient gender is '<gender>'
    When Trigger the post create request
    Then The request will be unsuccessful with the status code '400'
    And The Response JSONs should contain correct error message for '<error_type>'
    Examples:
    | gender        | error_type       |
    | random_text   | invalid_gender   |
    | empty         | empty_gender     |
    | number        | should_be_string |
    | gender_code   | invalid_gender   |
    | missing       | missing_gender   |



