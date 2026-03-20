@Search_Feature @functional
Feature: Search the immunization of a patient

    @Delete_cleanUp @supplier_name_TPP
    Scenario Outline: Verify that the GET method of Search API will be successful with all the valid parameters
        Given Valid vaccination record is created with Patient '<Patient>' and vaccine_type '<Vaccine_type>'
        When Send a search request with 'GET' method for Immunization event created
        Then The request will be successful with the status code '200'
        And The Search Response JSONs should contain the detail of the immunization events created above
        And The Search Response JSONs field values should match with the input JSONs field values for resourceType Immunization
        And The Search Response JSONs field values should match with the input JSONs field values for resourceType Patient
        Examples:
            | Patient        | Vaccine_type |
            | Random         | MMRV         |
            | SFlag          | RSV          |
            | SupersedeNhsNo | RSV          |
            | Random         | FLU          |
            | SFlag          | FLU          |
            | SupersedeNhsNo | FLU          |
            | Random         | COVID        |
            | SFlag          | PERTUSSIS    |
            | SupersedeNhsNo | COVID        |
            | Mod11_NHS      | RSV          |
            | Random         | SHINGLES     |
            | Random         | PNEUMOCOCCAL |


    @Delete_cleanUp @supplier_name_EMIS
    Scenario Outline: Verify that the POST method of Search API will be successful with all the valid parameters
        Given Valid vaccination record is created with Patient '<Patient>' and vaccine_type '<Vaccine_type>'
        When Send a search request with 'POST' method for Immunization event created
        Then The request will be successful with the status code '200'
        And The Search Response JSONs should contain the detail of the immunization events created above
        And The Search Response JSONs field values should match with the input JSONs field values for resourceType Immunization
        And The Search Response JSONs field values should match with the input JSONs field values for resourceType Patient
        Examples:
            | Patient        | Vaccine_type |
            | Random         | RSV          |
            | SFlag          | SHINGLES     |
            | SupersedeNhsNo | PERTUSSIS    |
            | Random         | FLU          |
            | SFlag          | 3IN1         |
            | SupersedeNhsNo | 4IN1         |
            | Random         | COVID        |
            | SFlag          | BCG          |
            | SupersedeNhsNo | HEPB         |

    @smoke
    @Delete_cleanUp @supplier_name_Postman_Auth
    Scenario Outline: Verify that the immunization events retrieved in the response of Search API should be within Date From and Date To range
        Given Valid vaccination record is created for '<NHSNumber>' and Disease Type '<vaccine_type>' with recorded date as '<DateFrom>'
        When Send a search request with 'GET' method with valid NHS Number '<NHSNumber>' and Disease Type '<vaccine_type>' and Date From '<DateFrom>' and Date To '<DateTo>'
        Then The request will be successful with the status code '200'
        And The occurrenceDateTime of the immunization events should be within the Date From and Date To range
        When Send a search request with 'POST' method with valid NHS Number '<NHSNumber>' and Disease Type '<vaccine_type>' and Date From '<DateFrom>' and Date To '<DateTo>'
        Then The request will be successful with the status code '200'
        And The occurrenceDateTime of the immunization events should be within the Date From and Date To range
        Examples:
            | NHSNumber  | vaccine_type | DateFrom   | DateTo     |
            | 9461267665 | FLU          | 2023-01-01 | 2023-06-04 |

    # Negative Scenarios
    @supplier_name_Postman_Auth
    Scenario Outline: Verify that Search API will throw error if NHS Number is invalid
        When Send a search request with 'GET' method with invalid NHS Number '<NHSNumber>' and valid Disease Type '<DiseaseType>'
        Then The request will be unsuccessful with the status code '400'
        And The Search Response JSONs should contain correct error message for invalid NHS Number
        When Send a search request with 'POST' method with invalid NHS Number '<NHSNumber>' and valid Disease Type '<DiseaseType>'
        Then The request will be unsuccessful with the status code '400'
        And The Search Response JSONs should contain correct error message for invalid NHS Number
        Examples:
            | NHSNumber         | DiseaseType |
            | ""                | COVID       |
            | 1234567890        | RSV         |
            | 1                 | COVID       |
            | 10000000000 00001 | COVID       |

    @smoke
    @supplier_name_Postman_Auth
    Scenario Outline: Verify that Search API will throw error if include is invalid
        When Send a search request with 'GET' method with valid NHS Number '<NHSNumber>' and valid Disease Type '<vaccine_type>' and invalid include '<include>'
        Then The request will be unsuccessful with the status code '400'
        And The Search Response JSONs should contain correct error message for invalid include
        When Send a search request with 'POST' method with valid NHS Number '<NHSNumber>' and valid Disease Type '<vaccine_type>' and invalid include '<include>'
        Then The request will be unsuccessful with the status code '400'
        And The Search Response JSONs should contain correct error message for invalid include
        Examples:
            | NHSNumber  | vaccine_type | include |
            | 9461267665 | COVID        | abc     |

    @smoke
    @supplier_name_Postman_Auth
    Scenario Outline: Verify that Search API will throw error if both different combination of dates and include is invalid
        When Send a search request with 'GET' method with valid NHS Number '<NHSNumber>' and valid Disease Type '<vaccine_type>' and Date From '<DateFrom>' and Date To '<DateTo>' and include '<include>'
        Then The request will be unsuccessful with the status code '400'
        And The Search Response JSONs should contain correct error message for invalid Date From, Date To and include
        When Send a search request with 'POST' method with valid NHS Number '<NHSNumber>' and valid Disease Type '<vaccine_type>' and Date From '<DateFrom>' and Date To '<DateTo>' and include '<include>'
        Then The request will be unsuccessful with the status code '400'
        And The Search Response JSONs should contain correct error message for invalid Date From, Date To and include
        Examples:
            | NHSNumber  | vaccine_type | DateFrom   | DateTo     | include              |
            | 9461267665 | COVID        | 999-06-01  | 999-06-01  | abc                  |
            | 9461267665 | COVID        | 2025-13-01 | 2025-12-01 | abc                  |
            | 9461267665 | COVID        | 2025-05-12 | 2025-05-12 | abc                  |
            | 9461267665 | COVID        | 999-06-01  | 999-06-01  | Immunization:patient |

    @smoke
    @supplier_name_Postman_Auth
    Scenario Outline: Verify that Search API will throw error if Disease Type is invalid
        When Send a search request with 'GET' method with valid NHS Number '<NHSNumber>' and invalid Disease Type '<DiseaseType>'
        Then The request will be unsuccessful with the status code '400'
        And The Search Response JSONs should contain correct error message for invalid Disease Type
        When Send a search request with 'POST' method with valid NHS Number '<NHSNumber>' and invalid Disease Type '<DiseaseType>'
        Then The request will be unsuccessful with the status code '400'
        And The Search Response JSONs should contain correct error message for invalid Disease Type
        Examples:
            | NHSNumber  | DiseaseType |
            | 9449304424 | ""          |
            | 9449304424 | FLu         |
            | 9449304424 | ABC         |

    @supplier_name_Postman_Auth
    Scenario Outline: Verify that Search API will throw error if both NHS Number and Disease Type are invalid
        When Send a search request with 'GET' method with invalid NHS Number '<NHSNumber>' and invalid Disease Type '<DiseaseType>'
        Then The request will be unsuccessful with the status code '400'
        And The Search Response JSONs should contain correct error message for invalid NHS Number as higher priority
        When Send a search request with 'POST' method with invalid NHS Number '<NHSNumber>' and invalid Disease Type '<DiseaseType>'
        Then The request will be unsuccessful with the status code '400'
        And The Search Response JSONs should contain correct error message for invalid NHS Number as higher priority
        Examples:
            | NHSNumber  | DiseaseType |
            | 1234567890 | ABC         |
            | ""         | ""          |

    @smoke
    @Delete_cleanUp @supplier_name_Postman_Auth
    Scenario: Verify that Search API returns 200 with results and OperationOutcome when both valid and invalid Disease Type are provided
        Given Valid vaccination record is created with Patient 'Random' and vaccine_type 'COVID'
        When Send a search request with 'GET' method with valid NHS Number and mixed valid and invalid Disease Type
        Then The request will be successful with the status code '200'
        And The Search Response should contain search results and OperationOutcome for invalid immunization targets
        When Send a search request with 'POST' method with valid NHS Number and mixed valid and invalid Disease Type
        Then The request will be successful with the status code '200'
        And The Search Response should contain search results and OperationOutcome for invalid immunization targets

    @smoke
    @Delete_cleanUp @supplier_name_MAVIS
    Scenario: Verify that Search API returns 200 with results and OperationOutcome with authorized and unauthorized Disease Type for the supplier
        Given Valid vaccination record is created with Patient 'Random' and vaccine_type 'FLU'
        When Send a search request with 'GET' method with valid NHS Number and multiple Disease Type
        Then The request will be successful with the status code '200'
        And The Search Response should contain search results and OperationOutcome for unauthorized immunization targets
        When Send a search request with 'POST' method with valid NHS Number and multiple Disease Type
        Then The request will be successful with the status code '200'
        And The Search Response should contain search results and OperationOutcome for unauthorized immunization targets


    @supplier_name_MAVIS @vaccine_type_RSV
    Scenario Outline: Verify that Search API will throw error if date from is invalid
        When Send a search request with 'GET' method with invalid Date From '<DateFrom>' and valid Date To '<DateTo>'
        Then The request will be unsuccessful with the status code '400'
        And The Search Response JSONs should contain correct error message for invalid Date From
        When Send a search request with 'POST' method with invalid Date From '<DateFrom>' and valid Date To '<DateTo>'
        Then The request will be unsuccessful with the status code '400'
        And The Search Response JSONs should contain correct error message for invalid Date From
        Examples:
            | DateFrom   | DateTo     |
            | 999-06-01  | 2025-06-01 |
            | 2025-13-01 | 2025-06-01 |
            | 2025-05-32 | 2025-06-01 |

    @supplier_name_RAVS @vaccine_type_RSV
    Scenario Outline: Verify that Search API will throw error if date to is invalid
        When Send a search request with 'GET' method with valid Date From '<DateFrom>' and invalid Date To '<DateTo>'
        Then The request will be unsuccessful with the status code '400'
        And The Search Response JSONs should contain correct error message for invalid Date To
        When Send a search request with 'POST' method with valid Date From '<DateFrom>' and invalid Date To '<DateTo>'
        Then The request will be unsuccessful with the status code '400'
        And The Search Response JSONs should contain correct error message for invalid Date To
        Examples:
            | DateFrom   | DateTo     |
            | 2025-05-01 | 999-06-01  |
            | 2025-05-01 | 2025-13-01 |
            | 2025-05-01 | 2025-05-32 |

    @supplier_name_MAVIS @vaccine_type_RSV
    Scenario Outline: Verify that Search API will throw error if both date from and date to are invalid
        When Send a search request with 'GET' method with invalid Date From '<DateFrom>' and invalid Date To '<DateTo>'
        Then The request will be unsuccessful with the status code '400'
        And The Search Response JSONs should contain correct error message for invalid Date From
        When Send a search request with 'POST' method with invalid Date From '<DateFrom>' and invalid Date To '<DateTo>'
        Then The request will be unsuccessful with the status code '400'
        And The Search Response JSONs should contain correct error message for invalid Date From
        Examples:
            | DateFrom   | DateTo     |
            | 999-06-01  | 999-06-01  |
            | 2025-13-01 | 2025-13-01 |
            | 2025-05-32 | 2025-05-32 |

    @smoke
    @supplier_name_SONAR
    Scenario Outline: Verify that Search API will throw error supplier is not authorized to make Search
        When Send a search request with 'GET' method with invalid NHS Number '<NHSNumber>' and valid Disease Type '<DiseaseType>'
        Then The request will be unsuccessful with the status code '403'
        And The Response JSONs should contain correct error message for 'unauthorized_access' access
        When Send a search request with 'POST' method with invalid NHS Number '<NHSNumber>' and valid Disease Type '<DiseaseType>'
        Then The request will be unsuccessful with the status code '403'
        And The Response JSONs should contain correct error message for 'unauthorized_access' access
        Examples:
            | NHSNumber  | DiseaseType |
            | 9449304424 | COVID       |

    @smoke
    @Delete_cleanUp @vaccine_type_FLU @patient_id_Random  @supplier_name_Postman_Auth
    Scenario: Flu event is created and updated twice and search request fetch the latest meta version and Etag
        Given I have created a valid vaccination record
        And created event is being updated twice
        When Send a search request with 'GET' method for Immunization event created
        Then The request will be successful with the status code '200'
        And The Search Response JSONs should contain the detail of the immunization events created above
        And The Search Response JSONs field values should match with the input JSONs field values for resourceType Immunization
        And The Search Response JSONs field values should match with the input JSONs field values for resourceType Patient

    @Delete_cleanUp @vaccine_type_FLU @patient_id_Random  @supplier_name_Postman_Auth
    Scenario: Flu event is created and search post request fetch the only one record matched with identifier
        Given I have created a valid vaccination record
        When I send a search request with Post method using identifier parameter for Immunization event created
        Then The request will be successful with the status code '200'
        And correct immunization event is returned in the response

    @smoke
    @Delete_cleanUp @vaccine_type_FLU @patient_id_NullNHS  @supplier_name_Postman_Auth
    Scenario: Search by Identifier (POST) is successful when patient does not have an NHS Number recorded
        Given I have created a valid vaccination record
        When I send a search request with Post method using identifier parameter for Immunization event created
        Then The request will be successful with the status code '200'
        And correct immunization event is returned in the response

    @Delete_cleanUp @vaccine_type_FLU @patient_id_Random  @supplier_name_Postman_Auth
    Scenario: Flu event is created and search post request fetch the only one record matched with identifier and _elements
        Given I have created a valid vaccination record
        When I send a search request with Post method using identifier and _elements parameters for Immunization event created
        Then The request will be successful with the status code '200'
        And correct immunization event is returned in the response with only specified elements

    @smoke
    @Delete_cleanUp @vaccine_type_HIB @patient_id_Random  @supplier_name_TPP
    Scenario: Flu event is created and search post request fetch the only one record matched with identifier with correct version id
        Given I have created a valid vaccination record
        And created event is being updated twice
        When I send a search request with Post method using identifier parameter for Immunization event created
        Then The request will be successful with the status code '200'
        And correct immunization event is returned in the response

    @smoke
    @Delete_cleanUp @vaccine_type_6IN1 @patient_id_Random  @supplier_name_EMIS
    Scenario: Flu event is created and search post request fetch the only one record matched with identifier and _elements with correct version id
        Given I have created a valid vaccination record
        And created event is being updated twice
        When I send a search request with Post method using identifier and _elements parameters for Immunization event created
        Then The request will be successful with the status code '200'
        And correct immunization event is returned in the response with only specified elements

    @smoke
    @vaccine_type_4IN1 @patient_id_Random  @supplier_name_Postman_Auth
    Scenario: Empty search response will be received when no record is found for the given identifier in search request
        When I send a search request with Post method using an invalid identifier header for Immunization event created
        Then The request will be successful with the status code '200'
        And Empty immunization event is returned in the response

    @smoke
    @Delete_cleanUp @supplier_name_TPP
    Scenario: Verify that Search API returns immunization events when searching by target-disease (GET)
        Given Valid vaccination record is created with Patient 'Random' and vaccine_type 'MMRV'
        When Send a search request with 'GET' method using target-disease for Immunization event created
        Then The request will be successful with the status code '200'
        And The Search Response JSONs should contain the detail of the immunization events created above

    @Delete_cleanUp @supplier_name_EMIS
    Scenario: Verify that Search API returns immunization events when searching by target-disease (POST)
        Given Valid vaccination record is created with Patient 'Random' and vaccine_type '3IN1'
        When Send a search request with 'POST' method using target-disease for Immunization event created
        Then The request will be successful with the status code '200'
        And The Search Response JSONs should contain the detail of the immunization events created above

    @Delete_cleanUp @supplier_name_Postman_Auth
    Scenario Outline: Verify that Search API will throw error if target-disease is used together with -immunization.target
        Given Valid vaccination record is created with Patient 'Random' and vaccine_type 'MMRV'
        When Send a search request with '<Method>' method using target-disease and -immunization.target for Immunization event created
        Then The request will be unsuccessful with the status code '400'
        And The Response JSONs should contain correct error message for invalid target-disease usage
        Examples:
            | Method |
            | GET    |
            | POST   |

    @Delete_cleanUp @supplier_name_Postman_Auth
    Scenario: Verify that Search API will throw error if target-disease is used together with identifier
        Given Valid vaccination record is created with Patient 'Random' and vaccine_type 'MMRV'
        When Send a search request with GET method using target-disease and identifier for Immunization event created
        Then The request will be unsuccessful with the status code '400'
        And The Response JSONs should contain correct error message for invalid target-disease usage

    @Delete_cleanUp @supplier_name_Postman_Auth
    Scenario: Verify that Search API returns immunization events when searching by comma-separated target-disease (GET)
        Given Valid vaccination record is created with Patient 'Random' and vaccine_type 'HEPB'
        When Send a search request with 'GET' method using comma-separated target-disease for Immunization event created
        Then The request will be successful with the status code '200'
        And The Search Response JSONs should contain the detail of the immunization events created above

    @Delete_cleanUp @supplier_name_Postman_Auth
    Scenario: Verify that Search API returns immunization events when searching by comma-separated target-disease (POST)
        Given Valid vaccination record is created with Patient 'Random' and vaccine_type 'COVID'
        When Send a search request with 'POST' method using comma-separated target-disease for Immunization event created
        Then The request will be successful with the status code '200'
        And The Search Response JSONs should contain the detail of the immunization events created above

    @smoke
    @Delete_cleanUp @supplier_name_TPP
    Scenario: Verify that immunization events retrieved by target-disease search are within Date From and Date To range
        Given Valid vaccination record is created for '9727805493' and Disease Type 'SHINGLES' with recorded date as '2023-01-15'
        When Send a search request with GET method using target-disease and Date From and Date To for Immunization event created
        Then The request will be successful with the status code '200'
        And The occurrenceDateTime of the immunization events should be within the Date From and Date To range
        When Send a search request with POST method using target-disease and Date From and Date To for Immunization event created
        Then The request will be successful with the status code '200'
        And The occurrenceDateTime of the immunization events should be within the Date From and Date To range

    @supplier_name_SONAR
    Scenario: Verify that Search API returns 403 when target-disease resolves only to vaccine types supplier is not authorised for
        When Send a search request with GET method using target-disease for Immunization event created with valid NHS Number and patient identifier system 'https://fhir.nhs.uk/Id/nhs-number' and target-disease system 'http://snomed.info/sct'
        Then The request will be unsuccessful with the status code '403'
        And The Response JSONs should contain correct error message for 'unauthorized_access' access

    @supplier_name_Postman_Auth
    Scenario: Verify that Search API returns 400 when all target-disease values are invalid SNOMED codes
        When Send a search request with 'GET' method with valid NHS Number and all invalid target-disease codes using patient identifier system 'https://fhir.nhs.uk/Id/nhs-number'
        Then The request will be unsuccessful with the status code '400'
        And The Response JSONs should contain correct error message for invalid target-disease codes
        When Send a search request with 'POST' method with valid NHS Number and all invalid target-disease codes using patient identifier system 'https://fhir.nhs.uk/Id/nhs-number'
        Then The request will be unsuccessful with the status code '400'
        And The Response JSONs should contain correct error message for invalid target-disease codes

    @smoke
    @Delete_cleanUp @supplier_name_Postman_Auth
    Scenario: Verify that Search API returns 200 with results and OperationOutcome when some target-disease values are invalid
        Given Valid vaccination record is created with Patient 'Random' and vaccine_type '6IN1'
        When Send a search request with 'GET' method using mixed valid and invalid target-disease codes for Immunization event created with target-disease system 'http://snomed.info/sct' and invalid target-disease code '99999'
        Then The request will be successful with the status code '200'
        And The Search Response should contain search results and OperationOutcome for invalid target-disease codes
        When Send a search request with 'POST' method using mixed valid and invalid target-disease codes for Immunization event created with target-disease system 'http://snomed.info/sct' and invalid target-disease code '99999'
        Then The request will be successful with the status code '200'
        And The Search Response should contain search results and OperationOutcome for invalid target-disease codes
