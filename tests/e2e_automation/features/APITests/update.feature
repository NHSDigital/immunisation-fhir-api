@Update_Feature @functional
Feature: Update the immunization of a patient

@smoke
@Delete_cleanUp @vaccine_type_RSV @patient_id_Random @supplier_name_RAVS
Scenario: Verify that the Update API will be successful with all the valid parameters
    Given I have created a valid vaccination record
    When Send a update for Immunization event created with patient address being updated
    Then The request will be successful with the status code '200'
    And The Etag in header will containing the latest event version
    And The X-Request-ID and X-Correlation-ID keys in header will populate correctly
    And The imms event table will be populated with the correct data for 'updated' event
    And The delta table will be populated with the correct data for updated event


@vaccine_type_RSV @patient_id_Random
Scenario: Verify that the updated event request will fail with forbidden access for MAVIS supplier
    Given valid vaccination record is created by 'RAVS' supplier 
    When Send a update for Immunization event created with patient address being updated by 'MAVIS'
    Then The request will be successful with the status code '403'
    And The Response JSONs should contain correct error message for 'forbidden' access


@delete_cleanup @vaccine_type_RSV @patient_id_Random @supplier_name_RAVS
Scenario: verify that vaccination record can be updated with valid vaccination detail
    Given I have created a valid vaccination record
    When Send a update for Immunization event created with vaccination detail being updated
    Then The request will be successful with the status code '200'
    And The Etag in header will containing the latest event version
    And The X-Request-ID and X-Correlation-ID keys in header will populate correctly
    And The imms event table will be populated with the correct data for 'updated' event
    And The delta table will be populated with the correct data for updated event   


@smoke
@Delete_cleanUp @vaccine_type_FLU @patient_id_Random  @supplier_name_Postman_Auth
Scenario: Flu event is created and updated twice
    Given I have created a valid vaccination record 
    When Send a update for Immunization event created with patient address being updated
    Then The request will be successful with the status code '200'
    And The Etag in header will containing the latest event version
    And The imms event table will be populated with the correct data for 'updated' event
    And The delta table will be populated with the correct data for updated event
    When Send a update for Immunization event created with vaccination detail being updated
    Then The request will be successful with the status code '200'
    And The Etag in header will containing the latest event version
    And The imms event table will be populated with the correct data for 'updated' event
    And The delta table will be populated with the correct data for updated event

@vaccine_type_FLU @patient_id_Random
Scenario: Verify that update will be successful when request is triggered by other supplier with authorize permission 
    Given valid vaccination record is created by 'Postman_Auth' supplier 
    When Send a update for Immunization event created with patient address being updated by 'MAVIS'
    Then The request will be successful with the status code '200'
    And The Etag in header will containing the latest event version
    And The imms event table will be populated with the correct data for 'updated' event
    And The delta table will be populated with the correct data for updated event

@Delete_cleanUp @vaccine_type_RSV @patient_id_Mod11_NHS @supplier_name_Postman_Auth
Scenario: Verify that the Update API will be successful with invalid but Mod11 compliant NHS Number
    Given I have created a valid vaccination record
    When Send a update for Immunization event created with patient address being updated
    Then The request will be successful with the status code '200'
    And The Etag in header will containing the latest event version
    And The X-Request-ID and X-Correlation-ID keys in header will populate correctly
    And The imms event table will be populated with the correct data for 'updated' event
    And The delta table will be populated with the correct data for updated event

@Delete_cleanUp @vaccine_type_RSV @patient_id_Mod11_NHS @supplier_name_Postman_Auth
Scenario Outline: Scenario Outline name: Verify that the Update API will be fails if occurrenceDateTime has future or invalid formatted date
    Given I have created a valid vaccination record
    When Send a update for Immunization event created with occurrenceDateTime being updated to '<Date>'
    Then The request will be unsuccessful with the status code '400'
    And The Response JSONs should contain correct error message for 'invalid_OccurrenceDateTime'
     Examples: 
        | Date                  | 
        | future_occurrence     | 
        | invalid_format        |
        | nonexistent           |
        | empty                 |

@Delete_cleanUp @vaccine_type_RSV @patient_id_Mod11_NHS @supplier_name_Postman_Auth
Scenario Outline: Scenario Outline name: Verify that the Update API will be fails if recorded has future or invalid formatted date
    Given I have created a valid vaccination record
    When Send a update for Immunization event created with recorded being updated to '<Date>'
    Then The request will be unsuccessful with the status code '400'
    And The Response JSONs should contain correct error message for 'invalid_recorded'
     Examples: 
        | Date                  | 
        | future_date           | 
        | invalid_format        |
        | nonexistent           |
        | empty                 |

@Delete_cleanUp @vaccine_type_RSV @patient_id_Mod11_NHS @supplier_name_Postman_Auth
Scenario Outline: Scenario Outline name: Verify that the Update API will be fails if expiration date has invalid formatted date
    Given I have created a valid vaccination record
    When Send a update for Immunization event created with expiration date being updated to '<Date>'
    Then The request will be unsuccessful with the status code '400'
   And The Response JSONs should contain correct error message for 'invalid_expirationDate'
     Examples: 
        | Date                  | 
        | invalid_format        |
        | nonexistent           |
        | empty                 |

@Delete_cleanUp @vaccine_type_RSV @patient_id_Mod11_NHS @supplier_name_Postman_Auth
Scenario Outline: Verify that the Update API will be fails if patient's date of birth has future or invalid formatted date
    Given I have created a valid vaccination record
    When Send a update for Immunization event created with patient date of bith being updated to '<Date>'
    Then The request will be unsuccessful with the status code '400'
    And The Response JSONs should contain correct error message for '<error_type>'
     Examples: 
        | Date                  | error_type            |   
        | future_date           | future_DateOfBirth    |
        | invalid_format        | invalid_DateOfBirth   |
        | nonexistent           | invalid_DateOfBirth   |
        | empty                 | invalid_DateOfBirth   |

@vaccine_type_3IN1 @patient_id_Random  @supplier_name_Postman_Auth
Scenario: Verify that the update request will fail for invalid immunization id
    When Send an update request for invalid immunization id
    Then The request will be unsuccessful with the status code '404'
    And The Response JSONs should contain correct error message for 'not_found'

@vaccine_type_3IN1 @patient_id_Random  @supplier_name_Postman_Auth
Scenario Outline: Verify that the update request will fail for invalid Etag value
    When Send an update request for invalid Etag <Etag>
    Then The request will be unsuccessful with the status code '400'
    And The Response JSONs should contain correct error message for etag 'invalid_etag'
        Examples:
        | Etag  |
        | 0     |
        | -1    |
        | abcde |
