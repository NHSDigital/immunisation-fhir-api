# Test application file
import json
import time
from pathlib import Path

from common.validator.validator import Validator

# TODO this needs to be converted to unit test with success and fail cases

parent_folder = Path(__file__).parent
data_folder = parent_folder / "data"
csvFilePath = data_folder / "test_data_ok.csv"  # Passes

dataType = 'CSV'

schemaFilePath = parent_folder / "schemas/test_school_schema.json"


start = time.time()

# get the JSON of the schema, changed to cope with elasticache
with open(schemaFilePath) as JSON:
    SchemaFile = json.load(JSON)

validator = Validator(SchemaFile)
error_report = validator.validate_csv(csvFilePath, False, True, True)

if len(error_report) > 0:
    print(error_report)
else:
    print('Validated Successfully')

end = time.time()
print(end - start)
