@Delete_Feature @functional
Feature: Delete an immunization of a patient

@vaccine_type_RSV @patient_id_Random @supplier_name_RAVS
Scenario: Verify that the Delete API will be successful with all the valid parameters
    Given I have created a valid vaccination record
    When Send a delete for Immunization event created
    Then The request will be successful with the status code '204'
    And The X-Request-ID and X-Correlation-ID keys in header will populate correctly
    And The imms event table will be populated with the correct data for 'deleted' event
    And The delta table will be populated with the correct data for deleted event

@vaccine_type_RSV @patient_id_Random @supplier_name_RAVS
Scenario: Verify that the Delete event is not coming in Get Search API response
    Given I have created a valid vaccination record
    When Send a delete for Immunization event created
    Then The request will be successful with the status code '204'
    And Deleted Immunization event will not be present in Get method Search API response

@vaccine_type_RSV @patient_id_Random @supplier_name_RAVS
Scenario: Verify that the Delete event is not coming in Post Search API response
    Given I have created a valid vaccination record
    When Send a delete for Immunization event created
    Then The request will be successful with the status code '204'
    And Deleted Immunization event will not be present in Post method Search API response

@vaccine_type_RSV @patient_id_Random
Scenario: Verify that the Delete event request will fail with unauthorized access for MAVIS supplier
    Given valid vaccination record is created by 'RAVS' supplier 
    When Send a delete for Immunization event created for the above created event is send by 'MAVIS'
    Then The request will be successful with the status code '403'
    And The Response JSONs should contain correct error message for 'unauthorized_access' access

@vaccine_type_RSV @patient_id_Random @supplier_name_RAVS
Scenario: Verify that the Delete event request will fail with Not found error
    When Send a delete for Immunization event created with invalid Imms Id 
    Then The request will be successful with the status code '404'
    And The Response JSONs should contain correct error message for Imms_id 'not_found'