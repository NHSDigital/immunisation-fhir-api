@Search_Feature @functional
Feature: Search the immunization of a patient

@smoke
@Delete_cleanUp @supplier_name_TPP
Scenario Outline: Verify that the GET method of Search API will be successful with all the valid parameters
    Given Valid vaccination record is created with Patient '<Patient>' and vaccine_type '<Vaccine_type>'
    When Send a search request with GET method for Immunization event created
    Then The request will be successful with the status code '200'
    And The Search Response JSONs should contain the detail of the immunization events created above
    And The Search Response JSONs field values should match with the input JSONs field values for resourceType Immunization
    And The Search Response JSONs field values should match with the input JSONs field values for resourceType Patient
    Examples: 
      |Patient       | Vaccine_type |
      |Random        | MMRV         |
      |SFlag         | RSV          |
      |SupersedeNhsNo| RSV          |
      |Random        | FLU          |
      |SFlag         | FLU          |
      |SupersedeNhsNo| FLU          |
      |Random        | COVID        |
      |SFlag         | PERTUSSIS    |
      |SupersedeNhsNo| COVID        |
      |Mod11_NHS     | RSV          |
      |Random        | SHINGLES     |
      |Random        | PNEUMOCOCCAL |

@smoke
@Delete_cleanUp @supplier_name_EMIS
Scenario Outline: Verify that the POST method of Search API will be successful with all the valid parameters 
    Given Valid vaccination record is created with Patient '<Patient>' and vaccine_type '<Vaccine_type>'
    When Send a search request with POST method for Immunization event created
    Then The request will be successful with the status code '200'
    And The Search Response JSONs should contain the detail of the immunization events created above
    And The Search Response JSONs field values should match with the input JSONs field values for resourceType Immunization
    And The Search Response JSONs field values should match with the input JSONs field values for resourceType Patient
    Examples: 
      |Patient       | Vaccine_type|
      |Random        | RSV         |
      |SFlag         | SHINGLES    |
      |SupersedeNhsNo| PERTUSSIS   |
      |Random        | FLU         |
      |SFlag         | 3IN1        |
      |SupersedeNhsNo| 4IN1        |
      |Random        | COVID       |
      |SFlag         | BCG         |
      |SupersedeNhsNo| HEPB        |

@supplier_name_Postman_Auth
Scenario Outline: Verify that the immunisation events retrieved in the response of Search API should be within Date From and Date To range
    When Send a search request with GET method with valid NHS Number '<NHSNumber>' and Disease Type '<vaccine_type>' and Date From '<DateFrom>' and Date To '<DateTo>'
    Then The request will be successful with the status code '200'
    And The occurrenceDateTime of the immunization events should be within the Date From and Date To range
    When Send a search request with POST method with valid NHS Number '<NHSNumber>' and Disease Type '<vaccine_type>' and Date From '<DateFrom>' and Date To '<DateTo>'
    Then The request will be successful with the status code '200'
    And The occurrenceDateTime of the immunization events should be within the Date From and Date To range
    Examples: 
      |NHSNumber        | vaccine_type | DateFrom   |  DateTo    |
      |9728403348       | FLU          | 2025-01-01 | 2025-06-04 |

# Negative Scenarios
@supplier_name_Postman_Auth
Scenario Outline: Verify that Search API will throw error if NHS Number is invalid
    When Send a search request with GET method with invalid NHS Number '<NHSNumber>' and valid Disease Type '<DiseaseType>'
    Then The request will be unsuccessful with the status code '400'
    And The Search Response JSONs should contain correct error message for invalid NHS Number
    When Send a search request with POST method with invalid NHS Number '<NHSNumber>' and valid Disease Type '<DiseaseType>'
    Then The request will be unsuccessful with the status code '400'
    And The Search Response JSONs should contain correct error message for invalid NHS Number
    Examples:
      | NHSNumber         | DiseaseType |
      |   ""              | COVID     |
      | 1234567890        | RSV         |
      | 1                 | COVID     |
      | 10000000000 00001 | COVID      |


@supplier_name_Postman_Auth 
Scenario Outline: Verify that Search API will throw error if include is invalid
    When Send a search request with GET method with valid NHS Number '<NHSNumber>' and valid Disease Type '<vaccine_type>' and invalid include '<include>'
    Then The request will be unsuccessful with the status code '400' 
    And The Search Response JSONs should contain correct error message for invalid include
    When Send a search request with POST method with valid NHS Number '<NHSNumber>' and valid Disease Type '<vaccine_type>' and invalid include '<include>'
    Then The request will be unsuccessful with the status code '400'
    And The Search Response JSONs should contain correct error message for invalid include
    Examples: 
      |NHSNumber        | vaccine_type | include  |
      |9728403348       | COVID      | abc      |


@supplier_name_Postman_Auth
Scenario Outline: Verify that Search API will throw error if both different combination of dates and include is invalid
    When Send a search request with GET method with valid NHS Number '<NHSNumber>' and valid Disease Type '<vaccine_type>' and Date From '<DateFrom>' and Date To '<DateTo>' and include '<include>'
    Then The request will be unsuccessful with the status code '400' 
    And The Search Response JSONs should contain correct error message for invalid Date From, Date To and include
    When Send a search request with POST method with valid NHS Number '<NHSNumber>' and valid Disease Type '<vaccine_type>' and Date From '<DateFrom>' and Date To '<DateTo>' and include '<include>'
    Then The request will be unsuccessful with the status code '400'
    And The Search Response JSONs should contain correct error message for invalid Date From, Date To and include
    Examples: 
      |NHSNumber        | vaccine_type | DateFrom   |  DateTo    | include                 |
      |9728403348       | COVID        | 999-06-01  | 999-06-01  | abc                     |
      |9728403348       | COVID        | 2025-13-01 | 2025-12-01 | abc                     |
      |9728403348       | COVID        | 2025-05-12 | 2025-05-12 | abc                     |
      |9728403348       | COVID        | 999-06-01  | 999-06-01  | Immunization:patient    |

@supplier_name_Postman_Auth
Scenario Outline: Verify that Search API will throw error if Disease Type is invalid
    When Send a search request with GET method with valid NHS Number '<NHSNumber>' and invalid Disease Type '<DiseaseType>'
    Then The request will be unsuccessful with the status code '400'
    And The Search Response JSONs should contain correct error message for invalid Disease Type
    When Send a search request with POST method with valid NHS Number '<NHSNumber>' and invalid Disease Type '<DiseaseType>'
    Then The request will be unsuccessful with the status code '400'
    And The Search Response JSONs should contain correct error message for invalid Disease Type
    Examples:
      | NHSNumber  |        DiseaseType       |
      | 9449304424 |        ""                |
      | 9449304424 |        FLu               |
      | 9449304424 |        ABC               |   

@supplier_name_Postman_Auth
Scenario Outline: Verify that Search API will throw error if both NHS Number and Disease Type are invalid
    When Send a search request with GET method with invalid NHS Number '<NHSNumber>' and invalid Disease Type '<DiseaseType>'
    Then The request will be unsuccessful with the status code '400'
    And The Search Response JSONs should contain correct error message for invalid NHS Number as higher priority
    When Send a search request with POST method with invalid NHS Number '<NHSNumber>' and invalid Disease Type '<DiseaseType>'
    Then The request will be unsuccessful with the status code '400'
    And The Search Response JSONs should contain correct error message for invalid NHS Number as higher priority
    Examples:
      | NHSNumber  |        DiseaseType       |
      | 1234567890 |        ABC               |
      |   ""       |        ""                |

@supplier_name_MAVIS @vaccine_type_RSV
Scenario Outline: Verify that Search API will throw error if date from is invalid
    When Send a search request with GET method with invalid Date From '<DateFrom>' and valid Date To '<DateTo>'
    Then The request will be unsuccessful with the status code '400'
    And The Search Response JSONs should contain correct error message for invalid Date From
    When Send a search request with POST method with invalid Date From '<DateFrom>' and valid Date To '<DateTo>'
    Then The request will be unsuccessful with the status code '400'
    And The Search Response JSONs should contain correct error message for invalid Date From
    Examples:
      | DateFrom      |        DateTo       |
      | 999-06-01     |        2025-06-01   |
      | 2025-13-01    |        2025-06-01   |    
      | 2025-05-32    |        2025-06-01   |    

@supplier_name_RAVS @vaccine_type_RSV
Scenario Outline: Verify that Search API will throw error if date to is invalid
    When Send a search request with GET method with valid Date From '<DateFrom>' and invalid Date To '<DateTo>'
    Then The request will be unsuccessful with the status code '400'
    And The Search Response JSONs should contain correct error message for invalid Date To
    When Send a search request with POST method with valid Date From '<DateFrom>' and invalid Date To '<DateTo>'
    Then The request will be unsuccessful with the status code '400'
    And The Search Response JSONs should contain correct error message for invalid Date To
    Examples:
      | DateFrom      |        DateTo       |
      | 2025-05-01    |        999-06-01    |
      | 2025-05-01    |        2025-13-01   |    
      | 2025-05-01    |        2025-05-32   |  

@supplier_name_MAVIS @vaccine_type_RSV
Scenario Outline: Verify that Search API will throw error if both date from and date to are invalid
    When Send a search request with GET method with invalid Date From '<DateFrom>' and invalid Date To '<DateTo>'
    Then The request will be unsuccessful with the status code '400'
    And The Search Response JSONs should contain correct error message for invalid Date From
    When Send a search request with POST method with invalid Date From '<DateFrom>' and invalid Date To '<DateTo>'
    Then The request will be unsuccessful with the status code '400'
    And The Search Response JSONs should contain correct error message for invalid Date From    
    Examples:
      | DateFrom      |        DateTo       |
      | 999-06-01     |        999-06-01    |
      | 2025-13-01    |        2025-13-01   |    
      | 2025-05-32    |        2025-05-32   |  


@supplier_name_SONAR
Scenario Outline: Verify that Search API will throw error supplier is not authorized to make Search 
    When Send a search request with GET method with invalid NHS Number '<NHSNumber>' and valid Disease Type '<DiseaseType>'
    Then The request will be unsuccessful with the status code '403'
    And The Response JSONs should contain correct error message for 'unauthorized_access' access
    When Send a search request with POST method with invalid NHS Number '<NHSNumber>' and valid Disease Type '<DiseaseType>'
    Then The request will be unsuccessful with the status code '403'
    And The Response JSONs should contain correct error message for 'unauthorized_access' access
    Examples:
      | NHSNumber   | DiseaseType |
      |  9449304424 | COVID       |

    
@Delete_cleanUp @vaccine_type_FLU @patient_id_Random  @supplier_name_Postman_Auth
Scenario: Flu event is created and updated twice and search request fetch the latest meta version and Etag
    Given I have created a valid vaccination record 
    And created event is being updated twice
    When Send a search request with GET method for Immunization event created
    Then The request will be successful with the status code '200'
    And The Search Response JSONs should contain the detail of the immunization events created above
    And The Search Response JSONs field values should match with the input JSONs field values for resourceType Immunization
    And The Search Response JSONs field values should match with the input JSONs field values for resourceType Patient

@Delete_cleanUp @vaccine_type_FLU @patient_id_Random  @supplier_name_Postman_Auth
Scenario: Flu event is created and search post request fetch the only one record matched with identifier
    Given I have created a valid vaccination record 
    When Send a search request with Post method using identifier header for Immunization event created
    Then The request will be successful with the status code '200'
    And correct immunization event is returned in the response

@Delete_cleanUp @vaccine_type_FLU @patient_id_Random  @supplier_name_Postman_Auth
Scenario: Flu event is created and search post request fetch the only one record matched with identifier and _elements
    Given I have created a valid vaccination record 
    When Send a search request with Post method using identifier and _elements header for Immunization event created
    Then The request will be successful with the status code '200'
    And correct immunization event is returned in the response with only specified elements

@Delete_cleanUp @vaccine_type_FLU @patient_id_Random  @supplier_name_Postman_Auth
Scenario: Flu event is created and search post request fetch the only one record matched with identifier with correct version id
    Given I have created a valid vaccination record
    And created event is being updated twice
    When Send a search request with Post method using identifier header for Immunization event created
    Then The request will be successful with the status code '200'
    And correct immunization event is returned in the response

@Delete_cleanUp @vaccine_type_FLU @patient_id_Random  @supplier_name_Postman_Auth
Scenario: Flu event is created and search post request fetch the only one record matched with identifier and _elements with correct version id
    Given I have created a valid vaccination record
    And created event is being updated twice
    When Send a search request with Post method using identifier and _elements header for Immunization event created
    Then The request will be successful with the status code '200'
    And correct immunization event is returned in the response with only specified elements

@vaccine_type_FLU @patient_id_Random  @supplier_name_Postman_Auth
Scenario: Empty search response will be received when no record is found for the given identifier in search request
    When Send a search request with post method using invalid identifier header for Immunization event created
    Then The request will be successful with the status code '200'
    And Empty immunization event is returned in the response  
    