variable "aws_region" {
    description = "Destination AWS region"
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

variable "prefix" {
  description = "Prefix for all resources"
}

variable "private_subnet_ids" {
  description = "IDs of the private subnets"
  type        = list(string)
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "ecs_sg_id" {
  description = "ID of the ECS security group"
  type        = string
}

# variable to hold aws_route_table.private[*].id
variable "route_table_ids" {
  description = "IDs of the route tables"
  type        = list(string)
}
