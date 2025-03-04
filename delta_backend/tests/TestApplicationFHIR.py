# Test application file
from pathlib import Path
from Converter import Converter
import json
import time


FHIR_data_folder = Path("C:/Source Code/Vaccs to JSON Converter/FHIR-data")
FHIRFilePath = FHIR_data_folder / "vaccination7.json"

start = time.time()

FHIRConverter = Converter(FHIRFilePath)
FlatFile = FHIRConverter.runConversion(False, True)

flatJSON = json.dumps(FlatFile)

if len(flatJSON) > 0:
    print(flatJSON)

errorRecords = FHIRConverter.getErrorRecords()

if len(errorRecords) > 0:
    print('Converted With Errors')
    print(errorRecords)
else: 
    print('Converted Successfully')

end = time.time()
print(end - start)



