# Id_Sync Lambda

## Overview

**Id Sync** is an AWS Lambda function designed to trigger from SQS. It receives a list of NHS Numbers and checks for changes in PDS. If change found, it updates the Events Table.

## Features

- **SQS Event Driven:** Automatically triggered by SQS event.
- **DynamoDb Integration:** Reviews contents of DynbamoDb Events table and updates where required..
- **Logging:** Provides detailed logging for monitoring and troubleshooting.

## How It Works

1. **SQS Event Trigger:** The Lambda is triggered by SQS events.
2. **File Processing:** The Lambda reads the NHS Number from SQS.
3. **DynamoDb Update:** If a new NHS Number is returned from PDS, all relevant records are updated with new value.
4. **Monitoring:** Logs are generated for each step, aiding in monitoring and debugging.

## Configuration

- **Environment Variables:**
  - `IEDS_TABLE_NAME`: Name of events table.
  - `PDS_ENV`: Targeted PDS service environment, eg INT.
  - `SPLUNK_FIREHOSE_NAME`: Name of the splunk firehose for logging

## Development

- Code is located in the `lambdas/id_sync/src/` directory.
- Unit tests are in the `lambdas/id_sync/tests/` directory.
- Use the provided Makefile and Dockerfile for building, testing, and packaging.

## License

This project is maintained by NHS. See [LICENSE](../LICENSE) for details.
