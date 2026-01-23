#!/bin/bash

# Build the Grafana docker image.
# This will be done manually. 
# We assume the ECR artifacts have been created already by the Makefile.

# Set variables

dirname=$(dirname "${0}")
DOCKERFILE_DIR=$(realpath "${dirname}")
echo "DOCKERFILE_DIR: ${DOCKERFILE_DIR}"

# Import the terraform's .env file; it should contain the ENVIRONMENT
source ../terraform/.env

# If it doesn't, prompt for the environment.
# Do not accept response if it is not one of the following
environments="prod|int|ref|dev"

if [[ ! "${ENVIRONMENT}" =~ ^${environments}$ ]] ; then
  echo "Invalid environment: ${ENVIRONMENT}"
  read -r -p "Please enter one of: $environments: " ENVIRONMENT
  if [[ ! "${ENVIRONMENT}" =~ ^${environments}$ ]] ; then
    echo "Invalid environment"
    exit 1
  fi
fi

# Set the prefix and other variables
PREFIX="imms-${ENVIRONMENT}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPOSITORY_NAME="${PREFIX}-grafana-app"
IMAGE_TAG="11.0.0-22.04_stable"
LOCAL_IMAGE_NAME="${REPOSITORY_NAME}:${IMAGE_TAG}"
IMAGE_NAME="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${LOCAL_IMAGE_NAME}"

# Generate a strong password. It will only ever appear in the build log, not in the repo.
# TODO: Re-tool this for the pipeline. Retrieve a password from Github Secrets, or AWS Secrets Manager
ADMIN_PW=$(tr -dc 'A-Za-z0-9!?%=' < /dev/random | head -c 12)
echo "*** Admin p/w: $ADMIN_PW"

# Change to the directory containing the Dockerfile
if ! cd "${DOCKERFILE_DIR}"; then
  echo "DOCKERFILE_DIR not found."
  exit 1
fi

# Check if Dockerfile exists
if [[ ! -f Dockerfile ]]; then
  echo "Dockerfile not found in DOCKERFILE_DIR."
  exit 1
fi

printf "Building and pushing Docker image to ECR...\n"
# Authenticate Docker to ECR
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

printf "Building Docker image...\n"
# Remove existing Docker image if it exists
docker rmi "${IMAGE_NAME}" --force

# Pull the base image for linux/amd64 architecture
docker pull --platform linux/amd64 grafana/grafana:latest

# Build Docker image for linux/amd64 architecture and push to ECR
docker buildx create --use
if ! docker buildx build --platform linux/amd64 --build-arg admin_pw="${ADMIN_PW}" -t "${IMAGE_NAME}" --push .; then
  echo "Docker build failed."
  exit 1
fi

# Inspect the built image
echo "Image: ${LOCAL_IMAGE_NAME}"

echo "Docker image built and pushed to ECR successfully."
