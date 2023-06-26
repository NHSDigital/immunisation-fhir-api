Feature: Immunisation Record Verification

    Background: I am testing the local environment
        Given I am testing the local environment

    Scenario Outline: Get Immunisation Records with mandatory fields
        When I retrieve immunisation records with the parameters nhsNumber=<nhsNumber>
        Then The response status code should be <status_code>
        And The response json should match <response_file>
        Examples:
            | nhsNumber | status_code | response_file                   |
            | 67547658  | 200         | immunisation_invalid_nhs_number |
            | 23838008  | 200         | immunisation_valid_nhs_number   |

    Scenario Outline: Search Immunisation Records
        When I search immunisation records with the parameters nhsNumber=<nhsNumber>
        Then The response status code should be <status_code>
        And The response json should match <response_file>
        Examples:
            | nhsNumber | status_code | response_file                 |
            | 23838008  | 200         | immunisation_valid_nhs_number |

    Scenario Outline: Delete immunisation Records
        When I delete immunisation records with the parameters nhsNumber=<nhsNumber> fullUrl=<fullUrl>
        Then The response status code should be <status_code>
        Examples:
            | nhsNumber | fullUrl                              | status_code | response_file                 |
            | 23838008  | 120f0d88-39df-402d-b9e2-5e74107f14c9 | 200         | immunisation_valid_nhs_number |

    Scenario Outline: Update immunisation Records
        When I update immunisation records with the parameters nhsNumber=<nhsNumber> fullUrl=<fullUrl>
        Then The response status code should be <status_code>
        Examples:
            | nhsNumber | fullUrl                              | status_code | response_file                 |
            | 23838008  | 120f0d88-39df-402d-b9e2-5e74107f14c9 | 200         | immunisation_valid_nhs_number |

    Scenario Outline: Get Immunisation Records with all fields
        When I retrieve immunisation records with the parameters nhsNumber=<nhsNumber>
        Then The response status code should be <status_code>
        And The response json should match <response_file>
        Examples:
            | nhsNumber | fullUrl                              | diseaseType  | from_date | to_date    | include_record | status_code | response_file                   |
            | 67547658  |                                      |              |           |            |                | 200         | immunisation_invalid_nhs_number |
            | 23838008  | 120f0d88-39df-402d-b9e2-5e74107f14c9 | Pneumococcal |           | 9999-01-01 |                | 200         | immunisation_valid_nhs_number   |
