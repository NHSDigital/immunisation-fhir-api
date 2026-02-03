# About

This document describes the purpose and environment setup for the recordforwarder Lambda.

## Overview

The Record Forwarder Lambda consumes from an AWS Kinesis Stream, and is responsible for applying updates to the Immunisation
Event Data Store. It will receive up to 100 records per batch. Each record will have been processed and formatted as a
FHIR Immunization by the ECS Record Processor in the prior batch step.

The Record Forwarded Lambda will then execute the requested operation (Create, Update or Delete) on the given record.

## Setting up the recordforwarder lambda

Note: Paths are relative to this directory, `recordforwarder`.

1. Follow the instructions in the root level README.md to setup the [dependencies](../README.md#environment-setup) and create a [virtual environment](../README.md#) for this folder.

2. Replace the `.env` file in the recordforwarder folder. Note the variables might change in the future. These environment variables will be loaded automatically when using `direnv`.

    ```
    AWS_PROFILE={your-profile}
    IMMUNIZATION_ENV={environment}
    ```

3. Run `poetry install --no-root` to install dependencies.

4. Run `make test` to run unit tests or individual tests by running:
    ```
    python -m unittest tests.test_fhir_batch_controller.TestCreateImmunizationBatchController
    python -m unittest tests.test_fhir_batch_controller.TestCreateImmunizationBatchController.test_send_request_to_dynamo_create_success
    ```
