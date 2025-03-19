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

### vpce vs nat gateway

By default, grafana image requires access to internet for plugins and updates. 
1. Disable internet access. The updates can be disabled and plugins can be preloaded. However, this was timeboxed and timed out.
2. Permit access via VPC Endpoints. This gives access to AWS services. However updates & & info updates require internet access by default. To avoid a natgw, a proxy could be used.
3. NatGateway - this is the current solutipn. However, it should be reviewed as it is more permissive and has higher costs.