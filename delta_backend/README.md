# 🩺 FHIR to Flat JSON Conversion Engine

This project is designed to convert FHIR-compliant JSON data (e.g., Immunization records) into a flat JSON format based on a configurable schema layout. It is intended to support synchronization of Immunisation API generated data from external sources to DPS (Data Processing System) data system

---

## 📁 File Structure Overview

| File Name              | What It Does |
|------------------------|---------------|
| **`converter.py`**     | 🧠 The main brain — applies the schema, runs conversions, handles errors. |
| **`FHIRParser.py`**    | 🪜 Knows how to dig into nested FHIR structures and pull out values like dates, IDs, and patient names. |
| **`SchemaParser.py`**  | Reads your schema layout and tells the converter which FHIR fields to extract and how to rename/format them. |
| **`ConversionLayout.py`** | A plain Python list that defines which fields you want, and how they should be formatted (e.g. date format, renaming rules). |
| **`ConversionChecker.py`** | 🔧 Handles transformation logic — e.g. turning a FHIR datetime into `YYYY-MM-DD`, applying lookups, gender codes, defaults, etc. |
| **`Extractor.py`**     | Specialized logic to pull practitioner names, site codes, addresses, and apply time-aware rules. |
| **`ExceptionMessages.py`** | Holds reusable error messages and codes for clean debugging and validation feedback. |

---


## 🛠️ Key Features

- Schema-driven field extraction and formatting
- Support for custom date formats like `YYYYMMDD`, and CSV-safe UTC timestamps
- Robust handling of patient, practitioner, and address data using time-aware logic
- Extendable structure with static helper methods and modular architecture

---

## Example Use Case

- Input: FHIR `Immunization` resource (with nested fields)
- Output: Flat JSON object with 34 standardized key-value pairs
- Purpose: To export into CSV or push into downstream ETL systems

---

## ✅ Getting Started with `check_conversion.py`

To quickly test your conversion, use the provided `check_conversion.py` script.
This script loads sample FHIR data, runs it through the converter, and automatically saves the output in both JSON and CSV formats.

### 🔄 How to Use It

1. Add your FHIR data (e.g., a dictionary or sample JSON) into the `fhir_sample` variable inside `check_conversion.py`
2. Ensure the field mapping in `ConversionLayout.py` matches your desired output
3. Run the script from the `tests` folder:

```bash
python check_conversion.py
```

### Output Location
When the script runs, it will automatically:
- Save a **flat JSON file** as `output.json`
- Save a **CSV file** as `output.csv`

These will be located one level up from the `tests/` folder:

```
/mnt/c/Users/USER/desktop/shn/immunisation-fhir-api/delta_backend/output.json
/mnt/c/Users/USER/desktop/shn/immunisation-fhir-api/delta_backend/output.csv
```

### Visualization
You can now:
- Open `output.csv` in Excel or Google Sheets to view cleanly structured records
- Inspect `output.json` to validate the flat key-value output programmatically

### TO REMOVED ONCE DONE
---
| Field Name Flat                        | Method Used                                       | Unit Tests |
|----------------------------------------|---------------------------------------------------|------------|
| PERSON_FORENAME                        | self.extractor.extract_person_forename            | ✅         |
| PERSON_SURNAME                         | self.extractor.extract_person_surname             | ✅         |
| PERSON_POSTCODE                        | self.extractor.extract_valid_address              | ✅         |
| SITE_CODE                              | self.extractor.extract_site_code                  | ✅         |
| SITE_CODE_TYPE_URI                     | self.extractor.extract_site_code_type_uri         | ✅         |
| PERFORMING_PROFESSIONAL_FORENAME       | self.extractor.extract_practitioner_forename      | ✅         |
| PERFORMING_PROFESSIONAL_SURNAME        | self.extractor.extract_practitioner_surname       | ✅         |
| VACCINATION_PROCEDURE_CODE             | self.extractor.extract_vaccination_procedure_code | ✅         |
| VACCINATION_PROCEDURE_TERM             | self.extractor.extract_vaccination_procedure_term | ✅         |
| DOSE_SEQUENCE                          | self.extractor.extract_dose_sequence              | ✅         |
| VACCINE_PRODUCT_CODE                   | self.extractor.extract_vaccine_product_code       | ✅         |
| VACCINE_PRODUCT_TERM                   | self.extractor.extract_vaccine_product_term       | ✅         |
| SITE_OF_VACCINATION_CODE               | self.extractor.extract_site_of_vaccination_code   | ✅         |
| SITE_OF_VACCINATION_TERM               | self.extractor.extract_site_of_vaccination_term   | ✅         |
| ROUTE_OF_VACCINATION_CODE              | self.extractor.extract_route_of_vaccination_code  | ✅         |
| ROUTE_OF_VACCINATION_TERM              | self.extractor.extract_route_of_vaccination_term  | ✅         |
| DOSE_AMOUNT                            | self.extractor.extract_dose_amount                | ✅         |
| DOSE_UNIT_CODE                         | self.extractor.extract_dose_unit_code             | ✅         |
| DOSE_UNIT_TERM                         | self.extractor.extract_dose_unit_term             | ✅         |
| INDICATION_CODE                        | self.extractor.extract_indication_code            | ✅         |
| LOCATION_CODE                          | self.extractor.extract_location_code              | ✅         |
| LOCATION_CODE_TYPE_URI                 | self.extractor.extract_location_code_type_uri     | ✅         |
| NHS_NUMBER                             | self.extract_nhs_number                           | ✅         |
| PERSON_DOB                             | self.extract_person_dob                           | ✅         |
| PERSON_GENDER_CODE                     | self.extract_person_gender                        | ✅         |
| DATE_AND_TIME                          | self.extract_date_and_time                        | ✅         |
| UNIQUE_ID                              | self.extract_unique_id                            | ✅         |
| UNIQUE_ID_URI                          | self.extract_unique_id_uri                        | ✅         |
| ACTION_FLAG                            |  INTERNAL                                         |  X         |
| RECORDED_DATE                          | self.extract_recorded_date                        |  ✅        |
| PRIMARY_SOURCE                         | self.extract_primary_source                       |  ✅        |
| VACCINE_MANUFACTURER                   | self.extract_vaccine_manufacturer                 |  ✅        |
| BATCH_NUMBER                           | self.extract_batch_number                         |  ✅        |
| EXPIRY_DATE                            | self.extract_expiry_date                          |  ✅        |
