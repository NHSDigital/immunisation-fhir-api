@Delete_Batch_Feature @functional
Feature: Create the immunization event for a patient through batch file and update the record from batch or Api calls

@smoke 
@vaccine_type_BCG  @supplier_name_TPP
Scenario: Delete immunization event for a patient through batch file
    Given batch file is created for below data as full dataset and each record has a valid delete record in the same file 
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
    And The imms event table will be populated with the correct data for 'deleted' event for records in batch file
    And The delta table will be populated with the correct data for all created records in batch file 
    And The delta table will be populated with the correct data for all deleted records in batch file 

@vaccine_type_MENB @patient_id_Random @supplier_name_EMIS
Scenario: Verify that the API vaccination record will be successful deleted by batch file upload
    Given I have created a valid vaccination record through API
    And The delta and imms event table will be populated with the correct data for api created event
    When An delete to above vaccination record is made through batch file upload
    And batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And bus ack will not have any entry of successfully processed records
    And Audit table will have correct status, queue name and record count for the processed batch file
    And The imms event table status will be updated to delete and no change to record detail 
    And The delta table will have delete entry with no change to record detail

@vaccine_type_RSV @patient_id_Random @supplier_name_RAVS
Scenario: Verify that the API vaccination record will be successful deleted and batch file will successful with mandatory field missing
    Given I have created a valid vaccination record through API
    When Delete above vaccination record is made through batch file upload with mandatory field missing
    And batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And bus ack will not have any entry of successfully processed records
    And The imms event table status will be updated to delete and no change to record detail 
    And The delta table will have delete entry with no change to record detail
