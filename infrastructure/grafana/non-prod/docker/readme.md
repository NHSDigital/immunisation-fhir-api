# Docker

## Introduction
This docker folder is used to deploy a grafana docker image to AWS ECR for use by ECS

## architecture
1. Dockerfile uses grafana/grafana:latest and is built for linux/amd64 for deploy to ECS
2. Entrypoint script `run.sh` starts grafana in a controlled manner and permits debug on startup

## To Build and deploy Grafana Docker image to AWS ECR

1. Start docker
2. execute `build_push_to_ecr.sh`
3. Success message "Docker image built and pushed to ECR successfully."
