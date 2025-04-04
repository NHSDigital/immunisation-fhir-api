## FHIR to Flat JSON Converter
This tool will convert FHIR immunisation resources to flat CSV JSON for use in the Sync process

## Usage
There is a test file showing the usage TestApplicationFHIR.py

The basic layout for conversion is below:

FHIR_data_folder = Path("C:/Source Code/Vaccs to JSON Converter/FHIR-data")
FHIRFilePath = FHIR_data_folder / "vaccination7.json"

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

## Changes
The above test uses a JSON vaccination file, but the FHIR parser will acccept JSON Data but the converter.py will need changing to accept JSPN data see def _getFHIRParser(self, filepath):

## Converter schema
The converter schema ConversionLayout.py has a breakdown of how the fields should be converted.
Example
    {
      "fieldNameFHIR": "site|coding|#:http://snomed.info/sct|display",
      "fieldNameFlat": "SITE_OF_VACCINATION_TERM",
      "expression": {
        "expressionName": "Look Up",
        "expressionType": "LOOKUP",
        "expressionRule": "site|coding|#:http://snomed.info/sct|code"
      }
    },

The fieldname is a view of the JSON filed we wish to identify, the pipes identify the node names in the FHIR resource
In the case of the example

site -
    coding -
        scan the array for the key or value of "http://snomed.info/sct" - 
            display

FHIR Data
    "site": {
      "coding": [
        {
          "system": "http://snomed.info/sct",
          "code": "368208006",
          "display": "Left upper arm structure (body structure)"
        }
      ]
    },

### Scanning arrays
if a FHIR node contains more than one entry, we can scan the array to identify either a key or a value that helps identify the array index we want to use.
Using the #: before the identifier allow us to say deep scan the array for a matching key or value
This will return the array index and the node assigned for the next key in the search.

so the field #:http://snomed.info/sct in the example state we should deep scan for "http://snomed.info/sct" in the array of site-coding and use the array index of the result to select the next key which is "display"

## Expressions 
Expressions allow us to run some functions on the data such as setting date-times to match the CSV data or set a defualt value in case it is missing.
The base conversion rules for flat JSON can be found in ConversionLayout.py

#### Expression function list

DATECONVERT : Convert dat time to the format in the expression rule e.g. "expressionRule": "%Y%m%d"
ONLYIF : Use the identified value only if a Key or Value can be found e.g. "expressionRule": "doseQuantity|system|http://snomed.info/sct" 
DEFAULT : Use this value if a value cannot be found in FHIR e.g. "expressionRule": "X99999" 
LOOKUP : Use another snomed code to lookup a snomed term if it cannot be found e.g. "expressionRule": "route|coding|#:http://snomed.info/sct|code". The look up data will be found in the LookUpData.py file
CHANGETO : Change the value to the value in expressionRule if it is found
GENDER : Change Gender by name to ID
NOTEMPTY : Base expression has no rule assigned

There are some other functions but they are currently not being used in the flat JSON conversion

## Conversion time
Reading a FHIR resource from file and converting to flat JSON take approximately 1ms per conversion








