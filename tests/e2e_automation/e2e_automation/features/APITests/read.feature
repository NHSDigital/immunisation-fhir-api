@Read_Feature @functional
Feature: Read the immunization of a patient

@Delete_cleanUp @supplier_name_MEDICUS
Scenario Outline: Verify that the Read method of API will be successful and fetch valid imms event detail 
    Given Valid vaccination record is created with Patient '<Patient>' and vaccine_type '<Vaccine_type>'
    When Send a read request for Immunization event created
    Then The request will be successful with the status code '200'
    And The Etag in header will containing the latest event version
    And The X-Request-ID and X-Correlation-ID keys in header will populate correctly
    And The Read Response JSONs field values should match with the input JSONs field values

    Examples: 
      |Patient       | Vaccine_type|
      |Random        | 4IN1        |
      |Random        | FLU         |
      |Random        | COVID       |


@Delete_cleanUp @vaccine_type_FLU @patient_id_Random  @supplier_name_Postman_Auth
Scenario: Flu event is created and updated twice and read request fetch the latest version and Etag
    Given I have created a valid vaccination record 
    And created event is being updated twice
    When Send a read request for Immunization event created
    Then The request will be successful with the status code '200'
    And The Etag in header will containing the latest event version
    And The X-Request-ID and X-Correlation-ID keys in header will populate correctly
    And The Read Response JSONs field values should match with the input JSONs field values

@vaccine_type_FLU @patient_id_Random  @supplier_name_Postman_Auth
Scenario: Deleted event returns 404 on read request
    Given I have created a valid vaccination record 
    And created event is being deleted
    When Send a read request for Immunization event created
    Then The request will be unsuccessful with the status code '404'
    And The Response JSONs should contain correct error message for 'not_found'

@vaccine_type_RSV @patient_id_Random @supplier_name_RAVS
Scenario: Verify that the Read event request will fail with Not found error with invalid Imms Id 
    When Send a read request for Immunization event created with invalid Imms Id 
    Then The request will be unsuccessful with the status code '404'
    And The Response JSONs should contain correct error message for Imms_id 'not_found'


