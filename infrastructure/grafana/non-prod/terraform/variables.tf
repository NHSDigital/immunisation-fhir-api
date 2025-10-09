variable "project_name" {
    default = "immunisations"
}

variable "project_short_name" {
    default = "imms"
}

variable "service" {
    default = "fhir-graf"
}

variable "aws_region" {
    description = "Destination AWS region"
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


variable "use_natgw" {
    description = "Boolean to determine whether to use the NAT Gateway module"
    type        = bool
    default     = true
}

variable "tags" {
    description = "A map of tags to add to all resources"
    type        = map(string)
    default     = {}
}

locals {
    environment = terraform.workspace == "green" ? "prod" : terraform.workspace == "blue" ? "prod" : terraform.workspace
    env         = terraform.workspace
    prefix      = "${var.project_short_name}-${local.env}-${var.service}"

    account_id = data.aws_caller_identity.current.account_id
    app_image  = "${local.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${local.prefix}-app:${var.app_version}"
    app_name   = "${local.prefix}-app"
    log_group  = "${local.prefix}-log"

    tags = {
        Environment = terraform.workspace
        Project     = local.prefix
    }
}
