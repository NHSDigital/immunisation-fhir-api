# Grafana infrastructure

The build comes in 2 parts
1. Docker image
2. AWS Infrastructure

## Docker Image

The docker file is built and pushed to the AWS ECT

The code may be found in the docker folder.

## Infrastructure

### Terraform state
S3 bucket name : immunisation-grafana-terraform-state 

The infrastructure is built using terraform. The code may be found in the terraform folder.

#### initialise terraform
The terraform  amanges multiple environmments. When running terraform init is used to specify the key dynamically using the -backend-config flag. This is done in the tf_init.sh file.

to rebuild the docker image from the ECR to ECS, run
```
terraform taint aws_ecs_task_definition.app
```

to review the docker image
```
docker image inspect imms-internal-dev-fhir-api-grafana:11.0.0-22.04_stable
docker image inspect imms-int-fhir-api-grafana:11.0.0-22.04_stable
docker image inspect imms-ref-fhir-api-grafana:11.0.0-22.04_stable
```

### building environments
Run the following commands to create and switch to the `int` workspace:
```
./tf_init.sh int
./tf_init.sh ref
./tf_init.sh internal-dev
'''

Create an environment
```
terraform workspace new int  
Build an environment
```
terraform workspace select int  
```

'''
terraform plan -var="environment=int"
'''

### vpce vs nat gateway

By default, grafana image requires access to internet for plugins and updates. 
1. Disable internet access. The updates can be disabled and plugins can be preloaded. However, this was timeboxed and timed out.
2. Permit access via VPC Endpoints. This gives access to AWS services. However updates & & info updates require internet access by default. To avoid a natgw, a proxy could be used.
3. NatGateway - this is the current solutipn. However, it should be reviewed as it is more permissive and has higher costs.