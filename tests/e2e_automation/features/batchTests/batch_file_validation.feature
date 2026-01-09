@Batch_File_Validation_Feature 
Feature: Validate the file level and columns validations for vaccination batch file

@vaccine_type_COVID  @supplier_name_MAVIS
Scenario Outline: verify that vaccination file will be rejected if file name format is invalid
    Given batch file is created for below data with <invalidFilename> filename and <file_extension> extension
        | patient_id        | unique_id         |
        | Random            | Valid_NhsNumber   |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has failure status for processed batch file
    And bus ack file will not be created
    And Audit table will have '<status>', '<queue_name>' and '<error_details>' for the processed batch file

    Examples:
        | invalidFilename           |  file_extension         |     status  |     queue_name              | error_details                                      |
        | HP_Vaccinations_v5_YGM41  | csv                     | Failed      |     unknown_unknown         | Initial file validation failed: invalid file key   |
        | HPV_Vaccinations_v5_YGM41 | pdf                     | Failed      |     unknown_unknown         | Initial file validation failed: invalid file key   |
        | HPV_Vaccination_v5_YGM41  | csv                     | Failed      |     unknown_unknown         | Initial file validation failed: invalid file key   |
        | HPV_Vaccinations_v0_YGM41 | csv                     | Failed      |     unknown_unknown         | Initial file validation failed: invalid file key   |
        | HPV_Vaccinations_v0_ABC12 | csv                     | Failed      |     unknown_unknown         | Initial file validation failed: invalid file key   |
 
@vaccine_type_HPV  @supplier_name_MAVIS
Scenario: verify that vaccination file will be rejected if the processed file is duplicate
    Given batch file is created for below data as full dataset
        | patient_id        | unique_id             |
        | Random            | Valid_NhsNumber       |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will be created
    And bus ack will not have any entry of successfully processed records
    And Audit table will have correct status, queue name and record count for the processed batch file
    When same batch file is uploaded again in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created for duplicate batch file upload
    And inf ack file has failure status for processed batch file
    And bus ack file will not be created
    And Audit table will have 'Not processed - Duplicate', 'MAVIS_HPV' and 'None' for the processed batch file

@vaccine_type_FLU  @supplier_name_MAVIS
Scenario: verify that vaccination file will be rejected if file is empty
    Given Empty batch file is created
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has success status for processed batch file
    And bus ack file will not be created
    And Audit table will have 'Not processed - Empty file', 'MAVIS_FLU' and 'None' for the processed batch file

@vaccine_type_MENACWY  @supplier_name_TPP
Scenario: verify that vaccination file will be rejected if columns are missing
    Given batch file is created with missing columns for below data
        | patient_id        | unique_id         |
        | Random            | Valid_NhsNumber   |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has failure status for processed batch file
    And bus ack file will not be created
    And Audit table will have 'Failed', 'TPP_MENACWY' and 'File headers are invalid.' for the processed batch file

@vaccine_type_COVID  @supplier_name_EMIS
Scenario: verify that vaccination file will be rejected if column order is invalid
    Given batch file is created with invalid column order for below data
        | patient_id        | unique_id         |
        | Random            | Valid_NhsNumber   |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has failure status for processed batch file
    And bus ack file will not be created
    And Audit table will have 'Failed', 'EMIS_COVID' and 'File headers are invalid.' for the processed batch file

@vaccine_type_FLU  @supplier_name_SONAR
Scenario: verify that vaccination file will be rejected if file delimiter is invalid
    Given batch file is created with invalid delimiter for below data
        | patient_id        | unique_id         |
        | Random            | Valid_NhsNumber   |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has failure status for processed batch file
    And bus ack file will not be created
    And Audit table will have 'Failed', 'SONAR_FLU' and 'File headers are invalid.' for the processed batch file

@vaccine_type_3IN1  @supplier_name_TPP
Scenario: verify that vaccination file will be rejected if one of the column name is invalid
    Given batch file is created with invalid column name for patient surname for below data
        | patient_id        | unique_id         |
        | Random            | Valid_NhsNumber   |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has failure status for processed batch file
    And bus ack file will not be created
    And Audit table will have 'Failed', 'TPP_3IN1' and 'File headers are invalid.' for the processed batch file

@vaccine_type_3IN1  @supplier_name_EMIS
Scenario: verify that vaccination file will be rejected if additional column is present
    Given batch file is created with additional column person age for below data
        | patient_id        | unique_id         |
        | Random            | Valid_NhsNumber   |
    When batch file is uploaded in s3 bucket
    Then file will be moved to destination bucket and inf ack file will be created
    And inf ack file has failure status for processed batch file
    And bus ack file will not be created
    And Audit table will have 'Failed', 'EMIS_3IN1' and 'File headers are invalid.' for the processed batch file