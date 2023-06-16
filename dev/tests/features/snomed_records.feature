Feature: Immunization Record Verification

    Background: I am testing the local environment
        Given I am testing the local environment

    Scenario Outline: Get Snomed Records
        When I retrieve snomed records with the parameters snomed_code=<snomed_code>
        Then The response status code should be <status_code>
        And The response json should match <response_file>
        Examples:
            | snomed_code | status_code | response_file                |
            | 67547658    | 200         | snomed_invalid_snomed_number |

    Scenario Outline: Delete Snomed Records
        When I delete snomed records with the parameters snomed_code=<snomed_code>
        Then The response status code should be <status_code>
        Examples:
            | snomed_code | status_code | response_file                |
            | 67547658    | 200         | snomed_invalid_snomed_number |

    Scenario Outline: Update Snomed Records
        When I update snomed records with the parameters snomed_code=<snomed_code>
        Then The response status code should be <status_code>
        Examples:
            | snomed_code | status_code | response_file                |
            | 67547658    | 200         | snomed_invalid_snomed_number |