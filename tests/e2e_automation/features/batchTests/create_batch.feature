@Create_Batch_Feature @functional
Feature: Create the immunization event for a patient through batch file

@smoke
@delete_cleanup_batch @vaccine_type_HPV  @supplier_name_TPP
Scenario: Verify that full dataset vaccination record will be created through batch file
    Given batch file is created for below data as full dataset
        | patient_id        | unique_id             |
        | Random            | Valid_NhsNumber       |
        | InvalidInPDS      | InvalidInPDS_NhsNumber|
        | SFlag             | SFlag_NhsNumber       |
        | Mod11_NHS         | Mod11_NhSNumber       |
        | OldNHSNo          | OldNHSNo              |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And bus ack will not have any entry of successfully processed records
    And Audit table will have correct status, queue name and record count for the processed batch file
    And The imms event table will be populated with the correct data for 'created' event for records in batch file
    And The delta table will be populated with the correct data for all created records in batch file  

@smoke
@delete_cleanup_batch @vaccine_type_MMR  @supplier_name_TPP 
Scenario: Verify that minimum dataset vaccination record will be created through batch file
    Given batch file is created for below data as minimum dataset
        | patient_id        | unique_id             |
        | Random            | Valid_NhsNumber       |
        | InvalidInPDS      | InvalidInPDS_NhsNumber|
        | SFlag             | SFlag_NhsNumber       |
        | Mod11_NHS         | Mod11_NhSNumber       |
        | OldNHSNo          | OldNHSNo              |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And bus ack will not have any entry of successfully processed records
    And Audit table will have correct status, queue name and record count for the processed batch file
    And The imms event table will be populated with the correct data for 'created' event for records in batch file
    And The delta table will be populated with the correct data for all created records in batch file  

@vaccine_type_FLU  @supplier_name_MAVIS
Scenario: Verify that vaccination record will be get rejected if date_and_time is invalid in batch file
    Given batch file is created for below data where date_and_time field has invalid date 
        | patient_id        | unique_id                                                |
        | Random            | Fail-future_occurrence-invalid_OccurrenceDateTime        |
        | Random            | Fail-invalid_batch_occurrence-invalid_OccurrenceDateTime |
        | Random            | Fail-nonexistent-invalid_OccurrenceDateTime              |
        | Random            | Fail-empty-empty_OccurrenceDateTime                      |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And all records are rejected in the bus ack file and no imms id is generated
    And Audit table will have correct status, queue name and record count for the processed batch file

@vaccine_type_6IN1  @supplier_name_EMIS
Scenario: verify that vaccination record will be get rejected if recorded_date is invalid in batch file
    Given batch file is created for below data where recorded field has invalid date 
        | patient_id        | unique_id                            |
        | Random            | Fail-future_date-invalid_recorded    |
        | Random            | Fail-invalid_format-invalid_recorded |
        | Random            | Fail-nonexistent-invalid_recorded    |
        | Random            | Fail-empty-empty_recorded            |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And all records are rejected in the bus ack file and no imms id is generated
    And Audit table will have correct status, queue name and record count for the processed batch file

@vaccine_type_4IN1  @supplier_name_TPP
Scenario: verify that vaccination record will be get rejected if expiry_date is invalid in batch file
    Given batch file is created for below data where expiry field has invalid date 
        | patient_id        | unique_id                                  |
        | Random            | Fail-invalid_format-invalid_expirationDate |
        | Random            | Fail-nonexistent-invalid_expirationDate    |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And all records are rejected in the bus ack file and no imms id is generated
    And Audit table will have correct status, queue name and record count for the processed batch file

@vaccine_type_FLU  @supplier_name_MAVIS
Scenario: verify that vaccination record will be get rejected if Person date of birth is invalid in batch file
    Given batch file is created for below data where Person date of birth field has invalid date 
        | patient_id        | unique_id                               |
        | Random            | Fail-future_date-future_DateOfBirth     |
        | Random            | Fail-invalid_format-invalid_DateOfBirth |
        | Random            | Fail-nonexistent-invalid_DateOfBirth    |
        | Random            | Fail-empty-missing_DateOfBirth          |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And all records are rejected in the bus ack file and no imms id is generated 
    And Audit table will have correct status, queue name and record count for the processed batch file

@vaccine_type_FLU  @supplier_name_MAVIS
Scenario: verify that vaccination record will be get rejected if Person nhs number, name and gender is invalid in batch file
    Given batch file is created for below data where Person detail has invalid data
        | patient_id        | unique_id                                        |                               
        | Random            | Fail-invalid_NhsNumber-invalid_nhsnumber_length  |
        | Random            | Fail-not_MOD11_NhsNumber-invalid_mod11_nhsnumber |
        | Random            | Fail-empty_patient_forename-no_forename          |
        | Random            | Fail-empty_patient_name-empty_forename_surname   |
        | Random            | Fail-empty_patient_surname-no_surname            |
        | Random            | Fail-invalid_gender_code-invalid_gender          |  
        | Random            | Fail-invalid_gender-invalid_gender               |  
        | Random            | Fail-empty_gender-missing_gender                 | 
        | Random            | Fail-white_space_forename-empty_array_item_forename            |
        | Random            | Fail-white_space_surname-empty_surname           | 
        | Random            | Fail-name_length_36-max_len_surname              | 
        | Random            | Fail-name_length_36-max_len_forename             | 
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And all records are rejected in the bus ack file and no imms id is generated
    And Audit table will have correct status, queue name and record count for the processed batch file 

@vaccine_type_BCG  @supplier_name_TPP
Scenario: verify that vaccination record will be get successful if performer is invalid in batch file
    Given batch file is created for below data where performer detail has invalid data
        | patient_id        | unique_id                |
        | Random            | empty_performer_forename |
        | Random            | empty_performer_Surname  |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And bus ack will not have any entry of successfully processed records
    And Audit table will have correct status, queue name and record count for the processed batch file
    And The imms event table will be populated with the correct data for 'created' event for records in batch file
    And The delta table will be populated with the correct data for all created records in batch file  

@vaccine_type_ROTAVIRUS  @supplier_name_TPP
Scenario: verify that vaccination record will be get successful with different valid value in gender field
    Given batch file is created for below data where person detail has valid values
        | patient_id        | unique_id                   |
        | Random            | gender_value_0              |
        | Random            | gender_value_1              |
        | Random            | gender_value_2              |
        | Random            | gender_value_9              |
        | Random            | gender_value_Not-Known      |
        | Random            | gender_value_male           |
        | Random            | gender_value_female         |
        | Random            | gender_value_not-Specified  |
        | Random            | patient_surname_max_length  |
        | Random            | patient_forename_max_length |
        | Random            | patient_forename_max_length_multiple_values |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And bus ack will not have any entry of successfully processed records
    And Audit table will have correct status, queue name and record count for the processed batch file
    And The imms event table will be populated with the correct data for 'created' event for records in batch file
    And The delta table will be populated with the correct data for all created records in batch file 

@vaccine_type_FLU  @supplier_name_MAVIS
Scenario: verify that vaccination record will be get rejected if mandatory fields for site, location and unique identifiers are missing in batch file
    Given batch file is created for below data where mandatory fields for site, location, action flag, primary source and unique identifiers are missing
        | patient_id        | unique_id                                             |                               
        | Random            | Fail-empty_site_code-empty_site_code                  |
        | Random            | Fail-empty_site_Code_uri-empty_site_code_uri          |
        | Random            | Fail-empty_location_code-empty_location_code          |
        | Random            | Fail-empty_location_code_uri-empty_location_code_uri  |
        | Random            | Fail-empty_unique_id-no_unique_identifiers            |
        | Random            | Fail-empty_unique_id_uri-no_unique_identifiers        |
        | Random            | Fail-empty_primary_source-empty_primary_source        |    
        | Random            | Fail-empty_procedure_code-no_procedure_code           | 
        | Random            | Fail-white_space_site_code-no_site_code               |
        | Random            | Fail-white_space_site_Code_uri-no_site_code_uri       |
        | Random            | Fail-white_space_location_code-no_location_code       |
        | Random            | Fail-white_space_location_Code_uri-no_location_code_uri|
        | Random            | Fail-white_space_unique_id-no_unique_id               |
        | Random            | Fail-white_space_unique_id_uri-no_unique_id_uri       | 
        | Random            | Fail-white_space_primary_source-no_primary_source     |  
        | Random            | Fail-white_space_procedure_code-empty_procedure_code  | 
        | Random            | Fail-invalid_primary_source-no_primary_source         | 
        | Random            | Fail-empty_action_flag-invalid_action_flag            |
        | Random            | Fail-white_space_action_flag-invalid_action_flag      |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And all records are rejected in the bus ack file and no imms id is generated
    And Audit table will have correct status, queue name and record count for the processed batch file 

@delete_cleanup_batch @vaccine_type_HIB  @supplier_name_EMIS
Scenario: verify that vaccination record will be successful if mandatory field for site, location and unique URI are invalid in batch file
    Given batch file is created for below data where mandatory field for site, location and unique uri values are invalid
        | patient_id        | unique_id                 |
        | Random            | invalid_unique_id_uri-    |
        | Random            | invalid_site_Code_uri-    |
        | Random            | invalid_location_Code_uri |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And bus ack will not have any entry of successfully processed records
    And Audit table will have correct status, queue name and record count for the processed batch file
    And The imms event table will be populated with the correct data for 'created' event for records in batch file
    And The delta table will be populated with the correct data for all created records in batch file 


@delete_cleanup_batch @vaccine_type_MENACWY  @supplier_name_TPP
Scenario: verify that vaccination record will be get successful if action flag has different cases
    Given batch file is created for below data where action flag has different cases
        | patient_id        | unique_id             |
        | Random            | Action_flag_NEW       |
        | Random            | Action_flag_New       |
        | Random            | Action_flag_new       |
        | Random            | Action_flag_nEw       |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And bus ack will not have any entry of successfully processed records
    And Audit table will have correct status, queue name and record count for the processed batch file
    And The imms event table will be populated with the correct data for 'created' event for records in batch file
    And The delta table will be populated with the correct data for all created records in batch file


@vaccine_type_3IN1  @supplier_name_TPP
Scenario: verify that vaccination record will be get rejected if non mandatory fields are empty string in batch file
    Given batch file is created for below data where non mandatory fields are empty string
        | patient_id        | unique_id             |
        | Random            | Fail-empty_NHS_Number-empty_NHSNumber       |
        | Random            | Fail-empty_procedure_term-empty_procedure_term       |  
        | Random            | Fail-empty_product_code-empty_product_code       |
        | Random            | Fail-empty_product_term-empty_product_term       |
        | Random            | Fail-empty_VACCINE_MANUFACTURER-empty_manufacturer       |
        | Random            | Fail-empty_batch_number-empty_lot_number       |
        | Random            | Fail-empty_site_OF_vaccination-empty_vaccine_site_code       |  
        | Random            | Fail-empty_site_OF_vaccination_term-empty_vaccine_site_term       |
        | Random            | Fail-empty_ROUTE_OF_vaccination-empty_route_code       |
        | Random            | Fail-empty_ROUTE_OF_vaccination_term-empty_route_term       |
        | Random            | Fail-empty_DOSE_SEQUENCE-doseNumberPositiveInt_PositiveInteger       | 
        | Random            | Fail-empty_dose_unit_code-empty_doseQuantity_code       |        
        | Random            | Fail-empty_dose_unit_term-empty_doseQuantity_term       |
        | Random            | Fail-empty_indication_code-empty_indication_code       |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And all records are rejected in the bus ack file and no imms id is generated
    And Audit table will have correct status, queue name and record count for the processed batch file  

@delete_cleanup_batch @vaccine_type_3IN1  @supplier_name_TPP
Scenario: verify that vaccination record will be get successful if non mandatory fields are missing in batch file
    Given batch file is created for below data where non mandatory fields are missing
        | patient_id        | unique_id             |
        | Random            | no_NHS_Number       |
        | Random            | no_procedure_term       |
        | Random            | no_product_code       |
        | Random            | no_product_term       |
        | Random            | no_VACCINE_MANUFACTURER       |
        | Random            | no_batch_number       |
        | Random            | no_site_OF_vaccination       |
        | Random            | no_site_OF_vaccination_term       |
        | Random            | no_ROUTE_OF_vaccination       |
        | Random            | no_ROUTE_OF_vaccination_term      |
        | Random            | no_DOSE_SEQUENCE       |
        | Random            | no_dose_unit_code       |
        | Random            | no_dose_unit_term       |
        | Random            | no_indication_code       |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And bus ack will not have any entry of successfully processed records
    And Audit table will have correct status, queue name and record count for the processed batch file
    And The imms event table will be populated with the correct data for 'created' event for records in batch file
    And The delta table will be populated with the correct data for all created records in batch file
