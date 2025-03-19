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

variable "public_subnet_ids" {
  description = "IDs of the public subnets"
  type        = list(string)
}
