
# About
This document describes the environment setup for the backend API Lambda.
This Lambda handles incoming CRUD operation requests from APIGEE and interacts with the immunisation events database to store immunisation records. All commands listed below are run in the `./backend` folder.

## Setting up the backend lambda
Note: Paths are relative to this directory, `backend`.

1. Follow the instructions in the root level README.md to setup the [dependencies](../README.md#environment-setup) and create a [virtual environment](../README.md#) for this folder.

2. Replace the `.env` file in the backend folder. Note the variables might change in the future. These environment variables will be loaded automatically when using `direnv`.
    ```
    AWS_PROFILE={your-profile}
    DYNAMODB_TABLE_NAME=imms-{environment}-imms-events
    IMMUNIZATION_ENV={environment}
    SPLUNK_FIREHOSE_NAME=immunisation-fhir-api-{environment}-splunk-firehose
    ```

3. Run `poetry install --no-root` to install dependencies.

4. Run `make test` to run unit tests or individual tests by running:
    ```
    python -m unittest tests.test_fhir_controller.TestSearchImmunizations
    python -m unittest tests.test_fhir_controller.TestSearchImmunizations.test_search_immunizations
    ```
