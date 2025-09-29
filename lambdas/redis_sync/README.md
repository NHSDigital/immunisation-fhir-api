# Redis Sync Lambda

## Overview

**Redis Sync** is an AWS Lambda function designed to monitor a configuration S3 bucket and synchronize its contents with an ElastiCache Redis instance. Whenever a new configuration file is uploaded or updated in the S3 bucket, the Lambda function processes the file, applies any required transformations, and uploads the result to the Redis cache.

## Features

- **S3 Event Driven:** Automatically triggered by S3 events (e.g., file uploads or updates) in the config bucket.
- **Transformation Support:** Applies custom transformation logic to configuration files before caching.
- **Redis Integration:** Uploads processed configuration data to ElastiCache Redis for fast, centralized access.
- **Logging:** Provides detailed logging for monitoring and troubleshooting.

## How It Works

1. **S3 Event Trigger:** The Lambda is triggered by S3 events on the config bucket.
2. **File Processing:** The Lambda reads the new or updated file from S3.
3. **Transformation:** If required, the file content is transformed to the appropriate format.
4. **Redis Upload:** The transformed data is uploaded to the Redis cache under a key corresponding to the file.
5. **Monitoring:** Logs are generated for each step, aiding in monitoring and debugging.

## Configuration

- **Environment Variables:**
  - `CONFIG_BUCKET_NAME`: Name of the S3 bucket to monitor.
  - `AWS_REGION`: AWS region for S3 and Redis.
  - `REDIS_HOST`: Redis endpoint.
  - `REDIS_PORT`: Redis port (default: 6379).

## Usage

1. **Deploy the Lambda** using your preferred IaC tool (e.g., Terraform, AWS SAM).
2. **Configure S3 event notifications** to trigger the Lambda on object creation or update.
3. **Ensure Redis and S3 permissions** are set for the Lambda execution role.

## Development

- Code is located in the `src/` directory.
- Unit tests are in the `tests/` directory.
- Use the provided Makefile and Dockerfile for building, testing, and packaging.

## License

This project is maintained by NHS. See [LICENSE](../LICENSE) for details.