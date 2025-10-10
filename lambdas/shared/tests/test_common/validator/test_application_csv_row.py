# Test application file
from pathlib import Path
from validator.validator import Validator
import json
import time

CSV_HEADER = 'academic_year,time_period,time_identifier,geographic_level,'
'country_code,country_name,region_code,region_name,new_la_code,la_name,'
'old_la_code,school_type,num_schools,enrolments,present_sessions,overall_attendance,'
'approved_educational_activity,overall_absence,authorised_absence,unauthorised_absence,'
'late_sessions,possible_sessions,reason_present_am,reason_present_pm,reason_present,'
'reason_l_present_late_before_registers_closed'
CSV_ROW = '202223,202223,Spring term,Local authority,E92000001,England,E12000004,'
'East Midlands,E06000016,Leicester,856,Primary,66.94915254,23057.94915,2367094,'
'2380687,13593,166808,99826,66982,34090,2547495,1157575,1180365,2337940,29154'
DATA_TYPE = 'CSVROW'

schema_data_folder = Path("C:/Source Code/CSV Validator/Schemas")
schemaFilePath = schema_data_folder / "test1.json"
# schemaFilePath = schema_data_folder / "test2.json"

start = time.time()

# get the JSON of the schema, moved from internal file to json string
# changed to cope with elasticache
with open(schemaFilePath, 'r') as JSON:
    SchemaFile = json.load(JSON)

Validator = Validator('', SchemaFile, CSV_ROW, CSV_HEADER, DATA_TYPE)
ErrorReport = Validator.runValidation(True, True, True)

if len(ErrorReport) > 0:
    print(ErrorReport)
else:
    print('Validated Successfully')

end = time.time()
print(end - start)
