# End-to-End Batch Test Suite (test_e2e_batch.py)

This test suite provides automated end-to-end (E2E) testing for the Immunisation FHIR API batch processing pipeline. It verifies that batch file submissions are correctly processed, acknowledged, and validated across the system.

## Overview

- Framework: Python unittest
- Purpose: Simulate real-world batch file submissions, poll for acknowledgements, and validate processing results.
- Test Scenarios: Defined in the scenarios module and enabled in setUp().
- Key Features:
    - Uploads test batch files to S3.
    - Waits for and validates ACK (acknowledgement) files.
    - Cleans up SQS queues and test artifacts after each run.

## Test Flow

1. Setup (setUp)

- Loads and enables a set of test scenarios.
- Prepares test data for batch submission.

2. Test Execution (test_batch_submission)

- Uploads ALL enabled test files to S3.
- Polls for ALL ACK responses and forwarded files.
- Validates the content and structure of ACK files.

3. Teardown (tearDown)

- Cleans up SQS queues and any generated test files.

## Key Functions

- send_files(tests): Uploads enabled test files to the S3 input bucket.
- poll_for_responses(tests, max_timeout): Polls for ACKs and processed files, with a timeout.
- validate_responses(tests): Validates the content of ACK files and checks for expected outcomes.

## How to Run

1. Ensure all dependencies and environment variables are set (see project root README).
2. Update `.env` file with contents indicated in `PR-NNN.env`, modified for PR
3. Update `.env` with reference to the appropriate AWS config profile `AWS_PROFILE={your-aws-profile}`
4. Update the apigee app to match the required PR-NNN
5. Run tests from vscode debugger or from makefile using

```
make test
```
