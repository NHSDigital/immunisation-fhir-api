
variable "aws_region" {
    description = "Destination AWS region"
}

variable "ec2_task_execution_role_name" {
    description = "ECS task execution role name"
}

variable "ecs_auto_scale_role_name" {
    description = "ECS auto scale role name"
}

variable "az_count" {
    description = "Number of AZs to cover in a given region"
}

variable "app_image" {
    description = "Docker image to run in the ECS cluster change to Grafana image in registry"
}

variable "app_port" {
    description = "Port exposed by the docker image to redirect traffic to"
}

variable "app_count" {
    description = "Number of docker containers to run"
}

variable "health_check_path" {
    description = "Health check path for the ALB"
}

variable "fargate_cpu" {
    description = "Fargate instance CPU units to provision (1 vCPU = 1024 CPU units)"
}

variable "fargate_memory" {
    description = "Fargate instance memory to provision (in MiB)"
}

variable "cidr_block" {
    description = "CIDR block for the VPC"
}