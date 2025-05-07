#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e


# Variables
image_name=sw-test-handlers
repo_name="sw-test-delta"
region="eu-west-2"
account_id="345594581768"
ecr_url="$account_id.dkr.ecr.$region.amazonaws.com"
dockerfile="Dockerfile"

# Build the Docker image using the specified Dockerfile
docker build --platform linux/amd64 -t $image_name:latest -f $dockerfile .

# Authenticate Docker to the ECR registry
aws ecr get-login-password --region $region | docker login --username AWS --password-stdin $ecr_url

# Create the ECR repository (if it doesn't already exist)
aws ecr create-repository --repository-name $repo_name --region $region || echo "Repository $repo_name already exists"

# Tag the Docker image with the ECR repository URL
docker tag $image_name:latest $ecr_url/$repo_name:latest

# Push the Docker image to the ECR repository
docker push $ecr_url/$repo_name:latest
