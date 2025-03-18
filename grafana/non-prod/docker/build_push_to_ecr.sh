#!/bin/bash

# Set variables

dirname=$(dirname "$0")
DOCKERFILE_DIR=$(realpath "$dirname")
echo "DOCKERFILE_DIR: $DOCKERFILE_DIR"

AWS_REGION="eu-west-2"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPOSITORY_NAME="imms-fhir-api-grafana"
IMAGE_TAG="11.0.0-22.04_stable"
LOCAL_IMAGE_NAME="$REPOSITORY_NAME:$IMAGE_TAG"
IMAGE_NAME="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$LOCAL_IMAGE_NAME"
TAGS="Key=Environment,Value=non-prod Key=Project,Value=immunisation-fhir-api-grafana"
LIFECYCLE_POLICY_FILE="lifecycle-policy.json"

# Change to the directory containing the Dockerfile
cd $DOCKERFILE_DIR

# Check if Dockerfile exists
if [ ! -f Dockerfile ]; then
  echo "Dockerfile not found in the current directory."
  exit 1
fi

# Create ECR repository if it does not exist
aws ecr describe-repositories --repository-names $REPOSITORY_NAME --region $AWS_REGION > /dev/null 2>&1

if [ $? -ne 0 ]; then
  echo "Creating ECR repository: $REPOSITORY_NAME"
  aws ecr create-repository --repository-name $REPOSITORY_NAME --region $AWS_REGION
  # Add tags to the repository
  aws ecr tag-resource --resource-arn arn:aws:ecr:$AWS_REGION:$ACCOUNT_ID:repository/$REPOSITORY_NAME --tags $TAGS
fi

# Apply lifecycle policy to the ECR repository
aws ecr put-lifecycle-policy --repository-name $REPOSITORY_NAME --lifecycle-policy-text file://$LIFECYCLE_POLICY_FILE --region $AWS_REGION

printf "Building and pushing Docker image to ECR...\n"
# Authenticate Docker to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

printf "Building Docker image...\n"
# Remove existing Docker image if it exists
docker rmi $IMAGE_NAME --force

# Pull the base image for linux/amd64 architecture
docker pull --platform linux/amd64 grafana/grafana:latest

# Build Docker image for linux/amd64 architecture and push to ECR
docker buildx create --use
docker buildx build --platform linux/amd64 -t $IMAGE_NAME --push .

# Check if the build was successful
if [ $? -ne 0 ]; then
  echo "Docker build failed."
  exit 1
fi

# Inspect the built image
echo "Image: $LOCAL_IMAGE_NAME"

echo "Docker image built and pushed to ECR successfully."