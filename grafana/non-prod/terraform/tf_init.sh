#!/bin/bash

# Exit immediately if a command fails
set -e

# Check if an environment is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <environment> [migrate|reconfigure]"
  exit 1
fi

ENVIRONMENT=$1
ACTION=${2:-""} # Optional second argument for migrate or reconfigure

# Define backend configuration
BUCKET="immunisation-grafana-terraform-state"
REGION="eu-west-2"
STATE_KEY="state/${ENVIRONMENT}/terraform.tfstate"

# Check if the S3 bucket exists, create it if it doesn't
if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "S3 bucket $BUCKET does not exist. Creating it..."
  aws s3api create-bucket \
    --bucket "$BUCKET" \
    --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION"

  # Enable versioning on the bucket
  echo "Enabling versioning on S3 bucket $BUCKET..."
  aws s3api put-bucket-versioning \
    --bucket "$BUCKET" \
    --versioning-configuration Status=Enabled
else
  echo "S3 bucket $BUCKET already exists."
fi

# Initialize Terraform with dynamic backend configuration
if [ "$ACTION" == "migrate" ]; then
  terraform init -migrate-state \
    -backend-config="key=${STATE_KEY}" \
    -backend-config="bucket=${BUCKET}" \
    -backend-config="region=${REGION}"
elif [ "$ACTION" == "reconfigure" ]; then
  terraform init -reconfigure \
    -backend-config="key=${STATE_KEY}" \
    -backend-config="bucket=${BUCKET}" \
    -backend-config="region=${REGION}"
else
  terraform init \
    -backend-config="key=${STATE_KEY}" \
    -backend-config="bucket=${BUCKET}" \
    -backend-config="region=${REGION}"
fi

echo "Terraform initialized for environment: ${ENVIRONMENT}"