variable "aws_region" {
    description = "Destination AWS region"
}

variable "ecs_auto_scale_role_name" {
    description = "ECS auto scale role name"
}

variable "az_count" {
    description = "Number of AZs to cover in a given region"
    default     = 2
}

variable "app_version" {
    description = "Version of the Docker image to run in the ECS cluster"
    default     = "11.0.0-22.04_stable"
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

variable "log_group" {
    description = "CloudWatch log group name"
}

variable "use_natgw" {
    description = "Boolean to determine whether to use the NAT Gateway module"
    type        = bool
    default     = true
}

variable "environment" {
    description = "Environment to deploy to"
}

variable "prefix" {
    description = "Prefix for all resources"
}

variable "tags" {
    description = "A map of tags to add to all resources"
    type        = map(string)
    default     = {}
}

locals {
    account_id = data.aws_caller_identity.current.account_id
    app_image  = "${local.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.prefix}:${var.app_version}"
    tags = {
        Environment = var.environment
        Project     = var.prefix
    }
}

output "app_image" {
    value = local.app_image
}