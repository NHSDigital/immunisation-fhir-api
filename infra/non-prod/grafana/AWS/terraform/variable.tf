# variables.tf
variable vpc_id {
  description = "The ID of the VPC to use"
  type        = string
}
variable "aws_region" {
    description = "Destination AWS region"
}

variable "ec2_task_execution_role_name" {
    description = "ECS task execution role name"
    default = "myEcsTaskExecutionRole"
}

variable "ecs_auto_scale_role_name" {
    description = "ECS auto scale role name"
    default = "myEcsAutoScaleRole"
}

variable "az_count" {
    description = "Number of AZs to cover in a given region"
    default = "1"
}

variable "app_image" {
    description = "Docker image to run in the ECS cluster change to Grafana image in registry"
    default = "123456789012.dkr.ecr.eu-west-2.amazonaws.com/grafana:latest"
}

variable "app_port" {
    description = "Port exposed by the docker image to redirect traffic to"
    default = 3000

}

variable "app_count" {
    description = "Number of docker containers to run"
    default = 1
}

variable "health_check_path" {
  default = "/"
}

variable "fargate_cpu" {
    description = "Fargate instance CPU units to provision (1 vCPU = 1024 CPU units)"
    default = "1024"
}

variable "fargate_memory" {
    description = "Fargate instance memory to provision (in MiB)"
    default = "2048"
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs"
  type        = list(string)
}
variable "cidr_block" {
  description = "The CIDR block of the VPC"
  type        = string
}

variable "main_route_table_id" {
  description = "The ID of the main route table"
  type        = string
}