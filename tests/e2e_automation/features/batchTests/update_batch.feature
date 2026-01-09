@Update_Batch_Feature @functional
Feature: Create the immunization event for a patient through batch file and update the record from batch or Api calls

@smoke 
@delete_cleanup_batch @vaccine_type_MMR  @supplier_name_TPP
Scenario: Update immunization event for a patient through batch file
    Given batch file is created for below data as full dataset and each record has a valid update record in the same file 
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
    And The imms event table will be populated with the correct data for 'updated' event for records in batch file
    And The delta table will be populated with the correct data for all created records in batch file 
    And The delta table will be populated with the correct data for all updated records in batch file 

@Delete_cleanUp @vaccine_type_ROTAVIRUS @patient_id_Random @supplier_name_EMIS
Scenario: Verify that the API vaccination record will be successful updated by batch file upload
    Given I have created a valid vaccination record through API
    And The delta and imms event table will be populated with the correct data for api created event
    When An update to above  vaccination record is made through batch file upload
    And batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And bus ack will not have any entry of successfully processed records
    And Audit table will have correct status, queue name and record count for the processed batch file
    And The imms event table will be populated with the correct data for 'updated' event for records in batch file
    And The delta table will be populated with the correct data for all updated records in batch file

@Delete_cleanUp @vaccine_type_6IN1 @patient_id_Random @supplier_name_TPP
Scenario: Verify that the batch vaccination record will be successful updated by API request
    Given batch file is created for below data as full dataset
        | patient_id        | unique_id             |
        | Random            | Valid_NhsNumber       |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And bus ack will not have any entry of successfully processed records
    And Audit table will have correct status, queue name and record count for the processed batch file
    And The imms event table will be populated with the correct data for 'created' event for records in batch file
    And The delta table will be populated with the correct data for all created records in batch file
    When Send a update for Immunization event created with vaccination detail being updated through API request
    Then Api request will be successful and tables will be updated correctly

@Delete_cleanUp @vaccine_type_RSV @patient_id_Random @supplier_name_RAVS
Scenario: Verify that the API vaccination record will be successful updated and batch file will fail upload due to mandatory field missing
    Given I have created a valid vaccination record through API
    When Update to above vaccination record is made through batch file upload with mandatory field missing
    And batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And bus ack will have error records for all the updated records in the batch file
    And The delta and imms event table will be populated with the correct data for api created event
