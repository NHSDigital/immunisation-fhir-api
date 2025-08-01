# Shared Lambda Components

## Overview

**Shared Lambda Components** is a reusable library containing common utilities, clients, and helper functions designed to be shared across multiple AWS Lambda functions in the immunisation FHIR API project. This package provides standardized implementations for database connections, AWS service clients, logging, validation, and other common operations.

## Purpose

This shared library promotes:
- **Code Reusability:** Common functionality used across multiple Lambda functions
- **Consistency:** Standardized patterns for AWS service interactions
- **Maintainability:** Centralized location for shared utilities and configurations
- **Efficiency:** Reduced code duplication and faster development

## Features

- **AWS Service Clients:** Pre-configured clients for DynamoDB, S3, SQS, SNS, and other AWS services
- **Database Utilities:** Common database operations and connection management
- **Logging Framework:** Standardized logging configuration and utilities
- **Validation Helpers:** Input validation and data transformation functions
- **Error Handling:** Common exception classes and error handling patterns
- **Configuration Management:** Environment variable handling and configuration utilities

## Components

### Core Modules

- **`clients.py`** - AWS service clients (DynamoDB, S3, SQS, etc.)
- **`logging_utils.py`** - Centralized logging configuration
- **`validators.py`** - Input validation and data transformation
- **`exceptions.py`** - Custom exception classes
- **`config.py`** - Environment configuration management
- **`utils.py`** - General utility functions

### Database Operations

- **`db_operations.py`** - Common database query patterns
- **`table_utils.py`** - DynamoDB table management utilities

### AWS Integrations

- **`s3_utils.py`** - S3 file operations
- **`sqs_utils.py`** - SQS message handling
- **`sns_utils.py`** - SNS notification utilities

## Usage

### In Lambda Functions

Import shared components in your Lambda functions:

```python
# Import AWS clients
from shared.clients import dynamodb_resource, s3_client

# Import utilities
from shared.logging_utils import setup_logger
from shared.validators import validate_nhs_number
from shared.exceptions import ValidationException

# Use in your Lambda function
logger = setup_logger(__name__)

def lambda_handler(event, context):
    try:
        # Use shared DynamoDB client
        table = dynamodb_resource.Table('my-table')

        # Use shared validation
        nhs_number = validate_nhs_number(event.get('nhs_number'))

        # Your Lambda logic here...

    except ValidationException as e:
        logger.error(f"Validation error: {e}")
        return {"statusCode": 400, "body": str(e)}
```

### Installation as Lambda Layer

This package is designed to be deployed as an AWS Lambda Layer for optimal reuse:

```bash
# Build the layer package
make build-layer

# Deploy as Lambda Layer (future implementation)
make deploy-layer
```

## Development

### Project Structure

```
shared/
├── src/
│   ├── common/
│   │   ├── clients.py
│   │   ├── logging_utils.py
│   │   ├── validators.py
│   │   ├── exceptions.py
│   │   └── config.py
│   ├── database/
│   │   ├── db_operations.py
│   │   └── table_utils.py
│   └── aws/
│       ├── s3_utils.py
│       ├── sqs_utils.py
│       └── sns_utils.py
├── tests/
│   ├── test_clients.py
│   ├── test_validators.py
│   └── test_utils.py
├── requirements.txt
├── Makefile
└── README.md
```

### Testing

```bash
# Run all tests
make test

# Run specific test
python -m pytest tests/test_clients.py

# Run with coverage
make test-coverage
```

### Building

```bash
# Install dependencies
make install

# Run linting
make lint

# Format code
make format

# Build package
make build
```

## Future Implementation: Lambda Layer Deployment

This shared library will be packaged and deployed as an AWS Lambda Layer to:

- **Reduce deployment package sizes** for individual Lambda functions
- **Enable version management** of shared components
- **Improve cold start performance** through layer caching
- **Simplify dependency management** across Lambda functions

### Planned Layer Structure

```
lambda-layer/
├── python/
│   └── shared/
│       ├── common/
│       ├── database/
│       └── aws/
└── layer.zip
```

### Usage with Layer

Once deployed as a layer, Lambda functions will reference it:

```python
# After layer deployment, import from layer
from shared.common.clients import dynamodb_resource
from shared.common.logging_utils import setup_logger
```

## Environment Variables

Common environment variables used by shared components:

- `AWS_REGION` - AWS region for service clients
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARN, ERROR)
- `ENVIRONMENT` - Environment name (dev, test, prod)

## Dependencies

See `requirements.txt` for Python package dependencies:
- `boto3` - AWS SDK
- `botocore` - AWS core library
- Additional utilities as needed

## Contributing

1. Follow existing code patterns and naming conventions
2. Add unit tests for new functionality
3. Update documentation for new components
4. Ensure backward compatibility when making changes

## Version Management

- **Semantic versioning** for layer releases
- **Changelog** documentation for version history
- **Compatibility matrix** for Lambda runtime versions

## License

This project is maintained by NHS. See [LICENSE](../LICENSE) for details.