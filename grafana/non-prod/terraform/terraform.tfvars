aws_region = "eu-west-2"

ecs_auto_scale_role_name = "EcsAutoScaleRole"

az_count = 2

app_port = 3000

app_count = 1

health_check_path = "/api/health"

fargate_cpu = 1024

fargate_memory = 2048

cidr_block = "10.0.0.0/16"

prefix = "imms-fhir-api-grafana"

app_version = "11.0.0-22.04_stable"

log_group = "/ecs/imms-fhir-api-grafana"

use_natgw = true

environment = "non-prod"