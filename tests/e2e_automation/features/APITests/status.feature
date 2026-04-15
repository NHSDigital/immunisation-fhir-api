@Status_feature @functional
Feature: Get the API status

@smoke @sandbox
Scenario: Verify that the /ping endpoint works
    When I send a request to the ping endpoint
    Then The request will be successful with the status code '200'

@smoke @sandbox
Scenario: Verify that the /status endpoint works
    Given the status API key is available in the given environment
    When I send a request to the status endpoint
    Then The request will be successful with the status code '200'
    And The status response will contain a passing healthcheck

@smoke
Scenario: Verify that clients cannot make a direct connection without mTLS to AWS backend
    When I send a direct request to the AWS backend
    Then The request is rejected

@smoke
Scenario: Verify that unauthenticated clients cannot get a successful response from the API
    When I send an unauthenticated request to the API
    Then The request will be unsuccessful with the status code '401'
