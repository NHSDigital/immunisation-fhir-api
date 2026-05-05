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

    @smoke
    @vaccine_type_ROTAVIRUS @patient_id_Random @supplier_name_TPP
    Scenario: Verify that the Delete request will fail when record is already soft deleted
        Given I have created a valid vaccination record
        When Send a delete for Immunization event created
        Then The request will be successful with the status code '204'
        And The X-Request-ID and X-Correlation-ID keys in header will populate correctly
        And The imms event table will be populated with the correct data for 'deleted' event
        And The delta table will be populated with the correct data for deleted event
        When same delete request is triggered again
        Then The request will be unsuccessful with the status code '404'
        And The Response JSONs should contain correct error message for Imms_id 'not_found'


    @vaccine_type_HEPB @patient_id_Random @supplier_name_TPP
    Scenario: Verify that the create request will be reinstated successfully after the record is soft deleted
        Given I have created a valid vaccination record
        When Send a delete for Immunization event created
        Then The request will be successful with the status code '204'
        And IMMS event and delta tables, along with the MNS event, will be populated with correct data for the deleted record
        When Trigger another post create request with same unique_id and unique_id_uri
        Then The request will be successful with the status code '201'
        And The location key and Etag in header will contain the  previous Immunization Id and version will be incremented by 1
        And IMMS event and delta tables, along with the MNS event, will be populated with correct created data for the reinstated record
        When Send a delete for Immunization event created
        Then The request will be successful with the status code '204'
        And IMMS event and delta tables, along with the MNS event, will be populated with correct data for the deleted record


    @vaccine_type_6IN1 @patient_id_Random @supplier_name_TPP
    Scenario: Verify that the update request is reinstated successfully after the record is soft deleted
        Given I have created a valid vaccination record
        When Send a delete for Immunization event created
        Then The request will be successful with the status code '204'
        And IMMS event and delta tables, along with the MNS event, will be populated with correct data for the deleted record
        When Trigger update request with same unique_id and unique_id_uri for the deleted record
        Then The request will be successful with the status code '200'
        And The Etag in header will contain the  correct version which will be incremented by 1
        And IMMS event and delta tables, along with the MNS event, will be populated with correct updated data for the reinstated record
        When Send a delete for Immunization event created
        Then The request will be successful with the status code '204'
        And IMMS event and delta tables, along with the MNS event, will be populated with correct data for the deleted record

    @vaccine_type_HEPB @patient_id_Random @supplier_name_TPP
    Scenario: Verify that the identifier search request will have empty response for deleted record
        Given I have created a valid vaccination record
        When Send a delete for Immunization event created
        Then The request will be successful with the status code '204'
        And IMMS event and delta tables, along with the MNS event, will be populated with correct data for the deleted record
        When I send a search request with Post method using identifier parameter for the record
        Then The request will be successful with the status code '200'
    #And No immunization event is returned in the response - defect need fixing for this VED-1263

    @vaccine_type_HEPB @patient_id_Random @supplier_name_TPP
    Scenario: Verify that the search request will have empty response for deleted record
        Given I have created a valid vaccination record
        When Send a delete for Immunization event created
        Then The request will be successful with the status code '204'
        And IMMS event and delta tables, along with the MNS event, will be populated with correct data for the deleted record
        When Send a search request with post method using patient.identifier and target-disease for Immunization event deleted
        Then The request will be successful with the status code '200'
        And No immunization event is returned in the response

    @Delete_cleanUp @vaccine_type_HEPB @patient_id_Random @supplier_name_TPP
    Scenario: Verify that the search request will be successful for reinstated record with create operation
        Given I have created a valid vaccination record
        When Send a delete for Immunization event created
        Then The request will be successful with the status code '204'
        And IMMS event and delta tables, along with the MNS event, will be populated with correct data for the deleted record
        When Trigger another post create request with same unique_id and unique_id_uri
        Then The request will be successful with the status code '201'
        And The location key and Etag in header will contain the  previous Immunization Id and version will be incremented by 1
        And IMMS event and delta tables, along with the MNS event, will be populated with correct created data for the reinstated record
        When I send a search request with Post method using identifier parameter for the record
        Then The request will be successful with the status code '200'
        And reinstated record is returned in the response with correct created data


    @Delete_cleanUp @vaccine_type_6IN1 @patient_id_Random @supplier_name_TPP
    Scenario: Verify that the search request will be successful for reinstated record with update operation
        Given I have created a valid vaccination record
        When Send a delete for Immunization event created
        Then The request will be successful with the status code '204'
        And IMMS event and delta tables, along with the MNS event, will be populated with correct data for the deleted record
        When Trigger update request with same unique_id and unique_id_uri for the deleted record
        Then The request will be successful with the status code '200'
        And The Etag in header will contain the  correct version which will be incremented by 1
        And IMMS event and delta tables, along with the MNS event, will be populated with correct updated data for the reinstated record
        When I send a search request with Post method using identifier parameter for the record
        Then The request will be successful with the status code '200'
        And reinstated record is returned in the response with correct created data

    @Delete_cleanUp @vaccine_type_HEPB @patient_id_Random @supplier_name_TPP
    Scenario: Verify that the create request will be unsuccessfully for already reinstated record
        Given I have created a valid vaccination record
        When Send a delete for Immunization event created
        Then The request will be successful with the status code '204'
        And IMMS event and delta tables, along with the MNS event, will be populated with correct data for the deleted record
        When Trigger another post create request with same unique_id and unique_id_uri
        Then The request will be successful with the status code '201'
        And The location key and Etag in header will contain the  previous Immunization Id and version will be incremented by 1
        And IMMS event and delta tables, along with the MNS event, will be populated with correct created data for the reinstated record
        When Trigger another post create request with same unique_id and unique_id_uri
        Then The request will be unsuccessful with the status code '422'
        And The Response JSONs should contain correct error message for 'duplicate'