# MNS Publisher Lambda

AWS Lambda function that processes immunisation vaccination records from SQS and publishes notifications to the Messaging Notification Service (MNS).

## Overview

The MNS Publisher Lambda function is responsible for:

- Processing SQS messages containing immunisation event data
- Extracting vaccination record details from DynamoDB stream events
- Creating MNS notification payloads following the CloudEvents specification
- Publishing notifications to the MNS for downstream processing
- Retrieving patient and practitioner details from PDS (Personal Demographics Service)

## Key Features

- **SQS Event Processing**: Consumes messages from SQS queues containing immunisation records
- **DynamoDB Stream Integration**: Parses DynamoDB stream event data for vaccination records
- **PDS Integration**: Retrieves patient demographic and practitioner details
- **Error Handling**: Comprehensive logging and error handling using AWS Lambda Powertools
- **Mock Service Support**: Includes mock MNS service for testing and development environments

## Architecture

### Event Flow

1. **SQS Trigger**: Lambda is triggered by messages from an SQS queue
2. **Record Processing**: Each message is processed to extract the vaccination event
3. **Notification Creation**: A CloudEvents-compliant notification is constructed with:
    - Patient demographics (NHS number, DOB, age at vaccination)
    - Vaccine details (vaccine type, site code)
    - Practitioner information (GP ODS code from PDS)
    - Immunisation URL reference
4. **MNS Publishing**: Notification is published to the configured MNS environment

### Notification Payload Structure

```json
{
    "specversion": "1.0",
    "id": "unique-notification-id",
    "source": "uk.nhs.vaccinations-data-flow-management",
    "type": "imms-vaccination-record-change-1",
    "datacontenttype": "application/fhir+json",
    "subject": "Immunisation|{imms-id}",
    "time": "ISO-8601-timestamp",
    "data": {
        "nhs_number": "patient-nhs-number",
        "vaccine_type": "vaccine-type",
        "patient_age": "age-at-vaccination",
        "gp_ods_code": "practitioner-ods-code",
        "immunisation_url": "reference-url"
    }
}
```

## Dependencies

- **python**: ~3.11
- **aws-lambda-typing**: ~2.20.0 - Type hints for AWS Lambda
- **aws-lambda-powertools**: 3.24.0 - AWS Lambda observability toolkit
- **boto3**: ~1.42.37 - AWS SDK
- **requests**: ^2.31.0 - HTTP client
- **pyjwt**: ^2.10.1 - JWT token handling

### Development Dependencies

- **coverage**: ^7.13.2 - Code coverage measurement
- **moto**: ~5.1.20 - AWS service mocking
- **mypy-boto3-dynamodb**: ^1.42.33 - Type hints for DynamoDB

## Installation

### Prerequisites

- Python 3.11+
- Poetry package manager
- Docker (for building Lambda deployment package)

### Local Setup

```bash
# Install dependencies using Poetry
poetry install

# Activate the virtual environment
source .venv/bin/activate
```

## Usage

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage report
make coverage-run
make coverage-report

# Generate HTML coverage report
make coverage-html
```

### Building Lambda Package

```bash
# Build Docker image
make build

# Package Lambda deployment artifact
make package

# Artifacts will be created in the ./build directory
```

## Environment Variables

The Lambda function requires the following environment variables:

- `MNS_ENV`: MNS environment configuration (default: "int")
    - Options: "int", "prod", or other configured environments
- `IMMUNIZATION_ENV`: Immunisation service environment
- `IMMUNIZATION_BASE_PATH`: Base path for immunisation service URL

## Configuration

The Lambda uses environment-based configuration:

- **MNS Service**: Automatically selects MnsService or MockMnsService based on MNS_ENV
- **Shared Dependencies**: Uses common utilities from `../shared/src` including:
    - MNS API client
    - PDS integration
    - Service URL resolution

## Code Structure

```
src/
├── lambda_handler.py       # Main Lambda entry point
├── process_records.py      # SQS record processing logic
├── create_notification.py  # MNS notification payload creation
├── observability.py        # Logging configuration
├── constants.py           # Static constants
└── __init__.py
```

### Key Modules

- **lambda_handler**: Entry point that receives SQS events
- **process_records**: Processes each SQS record and coordinates notification creation
- **create_notification**: Constructs the CloudEvents-compliant notification payload
- **observability**: AWS Lambda Powertools logger configuration

## Deployment

The Lambda is deployed as a Docker container image to AWS Lambda:

1. Build the Docker image containing the Lambda function
2. Push to AWS ECR (Elastic Container Registry)
3. Configure Lambda to use the container image
4. Set required environment variables
5. Configure SQS as the event source

## Error Handling

The function includes error handling for:

- Missing required fields (NHS number, DOB, vaccination date)
- PDS service failures (invalid NHS numbers, service unavailability)
- Invalid SQS message format
- MNS publishing failures

Errors are logged using AWS Lambda Powertools for observability and debugging.

## Monitoring and Observability

- Uses AWS Lambda Powertools for structured logging
- All processing steps are logged with context information
- Integration with CloudWatch for Lambda metrics and logs
- Error tracking and alerting through CloudWatch alarms

## Related Components

- **Shared Library**: `../shared/src/common` - Common utilities including MNS and PDS clients
- **Event Source**: Triggered by SQS messages from immunisation event processing pipeline
- **Downstream**: MNS processes published notifications for delivery to subscribed systems

## Contributing

When modifying this Lambda:

1. Update tests in the `tests/` directory
2. Run `make test` to verify changes
3. Ensure coverage remains above project thresholds
4. Update this README if adding new features or changing behavior
