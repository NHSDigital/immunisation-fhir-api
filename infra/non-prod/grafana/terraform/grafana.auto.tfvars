# terraform.tfvars

aws_region = "eu-west-2"

ec2_task_execution_role_name = "myEcsTaskExecutionRole"

ecs_auto_scale_role_name = "myEcsAutoScaleRole"

az_count = 1

app_image = "123456789012.dkr.ecr.eu-west-2.amazonaws.com/grafana:latest"

app_port = 3000

app_count = 1

health_check_path = "/"

fargate_cpu = "1024"

fargate_memory = "2048"

cidr_block = "10.0.0.0/16"

