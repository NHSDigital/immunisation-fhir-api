aws_region = "eu-west-2"

ec2_task_execution_role_name = "myEcsTaskExecutionRole"

ecs_auto_scale_role_name = "myEcsAutoScaleRole"

az_count = 2

#app_image = "public.ecr.aws/ubuntu/grafana:11.0.0-22.04_stable"
#@TODO remove account details and replace with placeholders to be derived from the environment
#app_image = "345594581768.dkr.ecr.eu-west-2.amazonaws.com/imms-fhir-api-grafana:11.0.0-22.04_stable"
app_image = "345594581768.dkr.ecr.eu-west-2.amazonaws.com/imms-fhir-api-grafana:hello-world"

app_port = 3000

app_count = 1

health_check_path = "/"

fargate_cpu = 1024

fargate_memory = 2048

cidr_block = "10.0.0.0/16"

prefix = "imms-fhir-api-grafana"

tags = {
  Environment = "non-prod"
  Project     = "immunisation-fhir-api"
}