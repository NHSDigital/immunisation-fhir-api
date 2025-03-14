# docker/build_push_to_ecr.sh

#!/bin/bash

# Set variables
AWS_REGION="eu-west-2"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPOSITORY_NAME="imms-fhir-api-grafana"
IMAGE_TAG="hello-world"
DOCKERFILE_DIR="/Users/watess01/Documents/NHS/code/immunisation-fhir-api/grafana/non-prod/docker"
TAGS="Key=Environment,Value=non-prod Key=Project,Value=immunisation-fhir-api-grafana"

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

printf "Building and pushing Docker image to ECR...\n"
# Authenticate Docker to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

printf "Building Docker image...\n"
# Build Docker image for linux/amd64 architecture
docker buildx create --use
docker buildx build --platform linux/amd64 -t $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPOSITORY_NAME:$IMAGE_TAG --push .

# Check if the build was successful
if [ $? -ne 0 ]; then
  echo "Docker build failed."
  exit 1
fi

echo "Docker image built and pushed to ECR successfully."

SERVICE=arn:aws:ecs:eu-west-2:345594581768:service/grafana-cluster/imms-fhir-api-grafana-ecs-svc

export AWS_PAGER=""
aws ecs update-service --cluster grafana-cluster --service imms-fhir-api-grafana-ecs-svc --force-new-deployment