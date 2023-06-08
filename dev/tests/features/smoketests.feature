Feature: SmokeTests
  Background: I am testing the local environment
    Given I am testing the local environment

  Scenario: Immunization Root Check
    When I invoke the root endpoint for the Immunization api
    Then The response status code should be 200
    And The response text should be FHIR API

  Scenario: Immunization Health Check
    When I invoke the health endpoint for the Immunization api
    Then The response status code should be 200
    And The response text should be empty

  Scenario Outline: Immunization Health Check2
    When I invoke the immunisation endpoint with the parameters <nhs_number> and <to_date>
    Then The response status code should be <status_code>
    # And The response text should be <response_text>
    Examples:
      |nhs_number|to_date|status_code|response_text|
      |675476587|9999-01-01|422|empty|
      |675476587|9999-01-01|422|empty|
