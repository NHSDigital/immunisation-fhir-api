# Test application file
from pathlib import Path
from common.validator.validator import Validator
import json
import time

csv_data_folder = Path("./data/csv-data/data")
# csvFilePath = csv_data_folder / "test_data.csv"  # Medium
csvFilePath = csv_data_folder / "test_data_ok.csv"  # Passes

dataType = 'CSV'

schema_data_folder = Path("C:/Source Code/CSV Validator/Schemas")
schemaFilePath = schema_data_folder / "test1.json"


start = time.time()

# get the JSON of the schema, changed to cope with elasticache
with open(schemaFilePath, 'r') as JSON:
    SchemaFile = json.load(JSON)

validator = Validator(csvFilePath, SchemaFile, '', '', dataType)
error_report = validator.run_validation(False, True, True)

if len(error_report) > 0:
    print(error_report)
else:
    print('Validated Successfully')

end = time.time()
print(end - start)
