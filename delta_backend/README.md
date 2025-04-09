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

---# 🩺 FHIR to Flat JSON Conversion Engine

This project is designed to convert FHIR-compliant JSON data (e.g., Immunization records) into a flat JSON format based on a configurable schema layout. It is intended to support synchronization of Immunisation API generated data from external sources to DPS (Data Processing System) data system

---

## 📁 File Structure Overview

| File Name              | What It Does |
|------------------------|---------------|
| **`converter.py`**     | 🧠 The main brain — applies the schema, runs conversions, handles errors. |
| **`FHIRParser.py`**    | 🪜 Knows how to dig into nested FHIR structures and pull out values like dates, IDs, and patient names. |
| **`SchemaParser.py`**  | 📐 Reads your schema layout and tells the converter which FHIR fields to extract and how to rename/format them. |
| **`ConversionLayout.py`** | ✍️ A plain Python list that defines which fields you want, and how they should be formatted (e.g. date format, renaming rules). |
| **`ConversionChecker.py`** | 🔧 Handles transformation logic — e.g. turning a FHIR datetime into `YYYY-MM-DD`, applying lookups, gender codes, defaults, etc. |
| **`Extractor.py`**     | 🎣 Specialized logic to pull practitioner names, site codes, addresses, and apply time-aware rules. |
| **`ExceptionMessages.py`** | 🚨 Holds reusable error messages and codes for clean debugging and validation feedback. |

---


## 🛠️ Key Features

- Schema-driven field extraction and formatting
- Support for custom date formats like `YYYYMMDD`, and CSV-safe UTC timestamps
- Robust handling of patient, practitioner, and address data using time-aware logic
- Extendable structure with static helper methods and modular architecture

---

## 📦 Example Use Case

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

### 📁 Output Location
When the script runs, it will automatically:
- Save a **flat JSON file** as `output.json`
- Save a **CSV file** as `output.csv`

These will be located one level up from the `src/` folder:

```
/mnt/c/Users/USER/desktop/shn/immunisation-fhir-api/delta_backend/output.json
/mnt/c/Users/USER/desktop/shn/immunisation-fhir-api/delta_backend/output.csv
```

### 👀 Visualization
You can now:
- Open `output.csv` in Excel or Google Sheets to view cleanly structured records
- Inspect `output.json` to validate the flat key-value output programmatically

---