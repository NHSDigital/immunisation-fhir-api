# Grafana infrastructure

The build comes in 2 parts

1. Docker image
2. AWS Infrastructure

## Docker Image

The docker file is built and pushed to the AWS ECR

The code may be found in the docker folder.

## Infrastructure

### Terraform state

S3 bucket name : immunisation-grafana-terraform-state

The infrastructure is built using terraform. The code may be found in the terraform folder.

#### initialise terraform

NOTE: Currently this process only runs locally. It is being reconstructed pending incorporation of the Grafana terraform into the infrastructure/account folder.

The script file `tf_init.sh` is no longer used. Instead a Makefile has been implemented.

### building environments

Run the following commands to create and switch to the `int` workspace:

1. Edit .env so that ENVIRONMENT is set to the desired environment (int, dev, prod, ref)
2. Create and build an environment.

```
terraform workspace new dev
terraform workspace select dev
make init
make plan
```

### vpce vs nat gateway

By default, grafana image requires access to internet for plugins and updates.

1. Disable internet access. The updates can be disabled and plugins can be preloaded. However, this was timeboxed and timed out.
2. Permit access via VPC Endpoints. This gives access to AWS services. However updates & & info updates require internet access by default. To avoid a natgw, a proxy could be used.
3. NatGateway - this is the current solution. However, it should be reviewed as it is more permissive and has higher costs.
