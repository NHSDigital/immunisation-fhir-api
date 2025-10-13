# Test application file
from pathlib import Path
from common.validator.validator import Validator
import json
import time


FHIR_data_folder = Path("C:/Source Code/CSV Validator/FHIR-data")
FHIRFilePath = FHIR_data_folder / "vaccination.json"

schema_data_folder = Path("C:/Source Code/CSV Validator/Schemas")
schemaFilePath = schema_data_folder / "schema.json"

DATA_TYPE = 'FHIRJSON'  # 'FHIR', 'FHIRJSON', 'CSV', 'CSVROW'

start = time.time()

# get the JSON of the schema, changed to cope with elasticache
with open(schemaFilePath, 'r') as JSON:
    SchemaFile = json.load(JSON)

# get the FHIR Data as JSON
with open(FHIRFilePath, 'r') as JSON:
    FHIRData = json.load(JSON)


validator = Validator(FHIRFilePath, FHIRData, SchemaFile, '', '', DATA_TYPE)  # FHIR File Path not needed
error_list = validator.runValidation(True, True, True)
error_report = validator.buildErrorReport('25a8cc4d-1875-4191-ac6d-2d63a0ebc64b')  # include the eventID if known

failed_validation = validator.hasValidationFailed()

# if len(ErrorList) > 0:
#     print(ErrorList)
# else:
#     print('Validated Successfully')

print('--------------------------------------------------------------------')
print(error_report)
print('--------------------------------------------------------------------')

if (failed_validation):
    print('Validation failed due to a critical validation failure...')
else:
    print('Validation Successful, see reports for details')


end = time.time()
print('Time Taken : ')
print(end - start)
