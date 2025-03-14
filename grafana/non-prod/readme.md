# Grafana infrastructure

The build comes in 2 parts
1. Docker image
2. AWS Infrastructure

## Docker Image

The docker file is built and pushed to the AWS ECT

The code may be found in the docker folder.

## Infrastructure

The infrastructure is built using terraform. The code may be found in the terraform folder.

to rebuild the docker image from the ECR to ECS, run
```
terraform taint aws_ecs_task_definition.app
```

to review the docker image
```
docker image inspect imms-fhir-api-grafana:11.0.0-22.04_stable
```
