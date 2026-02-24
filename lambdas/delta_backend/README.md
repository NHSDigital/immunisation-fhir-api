# 🩺 FHIR to Flat JSON Conversion Engine

This project is designed to convert FHIR-compliant JSON data (e.g., Immunization records) into a flat JSON format based on a configurable schema layout. It is intended to support synchronization of Immunisation API generated data from external sources to DPS (Data Processing System) data system

---

## 📁 File Structure Overview

| File Name                   | What It Does                                                                                                                 |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **`converter.py`**          | The main brain — applies the schema, runs conversions, handles errors.                                                       |
| **`conversion_layout.py`**  | A plain Python list that defines which fields you want, and how they should be formatted (e.g. date format, renaming rules). |
| **`delta.py`**              | Holds the function called by AWS Lambda.                                                                                     |
| **`extractor.py`**          | Tailored functionality to extract target fields from immunization record received by the delta handler.                      |
| **`exception_messages.py`** | Holds reusable error messages and codes for clean debugging and validation feedback.                                         |
| **`log_firehose.py`**       | Firehose logging functionality.                                                                                              |
| **`utils.py`**              | Holds utility functions.                                                                                                     |

---

## Setting up the delta lambda locally

Note: Paths are relative to this directory, `delta_backend`.

1. Follow the instructions in the root level README.md to setup the [dependencies](../README.md#environment-setup) and create a [virtual environment](../README.md#) for this folder.

2. Replace the `.env` file in the `delta_backend` folder. Note the variables might change in the future. These environment variables will be loaded automatically when using `direnv`.

    ```
    AWS_PROFILE=
    DYNAMODB_TABLE_NAME=
    IMMUNIZATION_ENV=
    SPLUNK_FIREHOSE_NAME=
    AWS_SQS_QUEUE_URL=
    DELTA_TABLE_NAME=
    SOURCE="local"
    ```

3. Run `poetry install` to install dependencies.

4. Run `make test` to run unit tests or `make coverage-run`. To see the unit test coverage, run `make coverage-run` first and then `make coverage-report`.

## Delta Stream Input Contract

This lambda consumes DynamoDB Stream records from `imms-<env>-imms-events` (`NEW_IMAGE`).

## Delta table indexing contract

For ordering-safe reads and backward compatibility, the delta table uses:

- Legacy GSI: `SearchIndex`
    - PK: `Operation`
    - SK: `DateTimeStamp`
- New GSI: `OperationSequenceIndex`
    - PK: `Operation`
    - SK: `DateTimeStampWithSequence`

`DateTimeStamp` is retained for DPS backward compatibility.
`DateTimeStampWithSequence` is for deterministic ordering of same-second events.

### Expected shape

```json
{
    "eventID": "stream-id",
    "eventName": "INSERT | MODIFY | REMOVE",
    "dynamodb": {
        "ApproximateCreationDateTime": 1690896000,
        "SequenceNumber": "4959...",
        "NewImage": {
            "PK": { "S": "covid#<imms-id>" },
            "SK": { "S": "covid#<patient-id>" },
            "Operation": { "S": "CREATE | UPDATE | DELETE | DELETE_LOGICAL" },
            "SupplierSystem": { "S": "EMIS | RAVS | ..." },
            "Resource": { "S": "{\"resourceType\":\"Immunization\", ... }" }
        },
        "Keys": {
            "PK": { "S": "covid#<imms-id>" }
        }
    }
}
```

### Compatibility rules

The processor accepts the following legacy/fallback inputs:

1. **Patient key fallback**
    - Preferred: `NewImage.SK`
    - Fallback: `NewImage.PatientSK`

2. **Operation fallback**
    - Preferred: `NewImage.Operation`
    - Fallback: mapped from `eventName`:
        - `INSERT -> CREATE`
        - `MODIFY -> UPDATE`
        - `REMOVE -> DELETE`

3. **Payload fallback**
    - Preferred: `NewImage.Resource` (FHIR JSON string, converted via `Converter`)
    - Fallback: `NewImage.Imms` (already-flat or JSON string), with `ACTION_FLAG` added when missing

4. **Sequence fallback**
    - Preferred: `dynamodb.SequenceNumber`
    - Fallback: `NewImage.SequenceNumber`
    - Final fallback: `"0"`

5. **Skip rules**
    - If `SupplierSystem` is `DPSFULL` or `DPSREDUCED`, record is skipped (logged, no DDB write)

### Output/behavior contract

- `process_record(...)` returns:
    - `tuple[bool, dict]` → `(success, operation_outcome)`
- `operation_outcome` always includes:
    - `record`
    - `operation_type`
    - `statusCode`
    - `statusDesc`
- Failed records are sent to DLQ.

## 🛠️ Key Features

- Schema-driven field extraction and formatting
- Support for custom date formats like `YYYYMMDD`, and CSV-safe UTC timestamps
- Robust handling of patient, practitioner, and address data using time-aware logic
- Extendable structure with static helper methods and modular architecture

---

## Example Use Case

- Input: FHIR `Immunization` resource (with nested fields)
- Output: Flat JSON object with 35 standardized key-value pairs
- Purpose: To export into CSV or push into downstream ETL systems

---

## ✅ Getting Started with `check_conversion.py`

To quickly test your conversion, use the provided `check_conversion.py` script.
This script loads sample FHIR data, runs it through the converter, and automatically saves the output in both JSON and CSV formats.

### 🔄 How to Use It

1. Add your FHIR data (e.g., a dictionary or sample JSON) into the `fhir_sample` variable inside `check_conversion.py`
2. Ensure the field mapping in `conversion_layout.py` matches your desired output
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
