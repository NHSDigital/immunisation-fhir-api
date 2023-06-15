Feature: Immunization Record Verification

    Background: I am testing the local environment
        Given I am testing the local environment

    Scenario Outline: Get Immunization Records
        When I retrieve immunization records with the parameters nhsNumber=<nhsNumber> to_date=<to_date>
        Then The response status code should be <status_code>
        And The response json should match <response_file>
        Examples:
            | nhsNumber | to_date    | status_code | response_file                   |
            | 67547658  | 9999-01-01 | 200         | immunization_invalid_nhs_number |
            | 23838008  | 9999-01-01 | 200         | immunization_valid_nhs_number   |

    Scenario Outline: Search Immunization Records
        When I search immunization records with the parameters nhsNumber=<nhsNumber>
        Then The response status code should be <status_code>
        And The response json should match <response_file>
        Examples:
            | nhsNumber | status_code | response_file                 |
            | 23838008  | 200         | immunization_valid_nhs_number |

    Scenario Outline: Delete Immunization Records
        When I delete immunization records with the parameters nhsNumber=<nhsNumber> fullUrl=<fullUrl>
        Then The response status code should be <status_code>
        Examples:
            | nhsNumber | fullUrl                              | status_code | response_file                 |
            | 23838008  | 120f0d88-39df-402d-b9e2-5e74107f14c9 | 200         | immunization_valid_nhs_number |