Feature: Immunization Record Verification

    Background: I am testing the local environment
        Given I am testing the local environment

    Scenario Outline: Get Immunization Records
        When I get the immunisation endpoint with the parameters nhsNumber=<nhsNumber> to_date=<to_date>
        Then The response status code should be <status_code>
        And The response json should match <response_file>
        Examples:
            | nhsNumber | to_date    | status_code | response_file                   |
            | 67547658  | 9999-01-01 | 200         | immunization_invalid_nhs_number |
            | 23838008  | 9999-01-01 | 200         | immunization_valid_nhs_number   |

    Scenario Outline: Search Immunization Records
        When I get the immunisation search endpoint with the parameters nhsNumber=<nhsNumber>
        Then The response status code should be <status_code>
        And The response json should match <response_file>
        Examples:
            | nhsNumber | status_code | response_file                 |
            | 23838008  | 200         | immunization_valid_nhs_number |