# Test application file
from pathlib import Path
from validator.parsers.fhir_parser import FHIRParser
import time

fhir_data_folder = Path("./data")
fhirFilePath = fhir_data_folder / "vaccination.json"

start = time.time()

fhir_parser = FHIRParser()
fhir_parser.parse_fhir_file(fhirFilePath)
my_value = fhir_parser.get_key_value('vaccineCode|coding|0|code')
print('Value = ', my_value)

end = time.time()
print('Time to Run : ', end - start)
