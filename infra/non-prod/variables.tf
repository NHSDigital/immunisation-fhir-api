data "aws_vpc" "default" {
    default = true
    // cidr = 172.31.0.0/16 
}

data "aws_route_table" "main" {
  vpc_id = data.aws_vpc.default.id

  filter {
    name   = "association.main"
    values = ["true"]
  }
}


data "aws_subnets" "default" {
    filter {
        name   = "vpc-id"
        values = [data.aws_vpc.default.id]
    }
}
data "aws_route_tables" "default_route_tables" {
  vpc_id = data.aws_vpc.default.id
}

variable "aws_region" {
    default = "eu-west-2"
}
variable "project_name" {
    default = "immunisation-batch"
}
variable "project_short_name" {
    default = "imms-batch"
}
locals {
    environment         = terraform.workspace
    account_id = local.environment == "prod" ? 232116723729 : 603871901111
    local_account_id = local.environment == "prod" ? 664418956997 : 345594581768
}
data "aws_kms_key" "existing_s3_encryption_key" {
  key_id = "alias/imms-batch-s3-shared-key"
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs"
  type        = list(string)
  default     = ["subnet-0c820f8e69aae7bcb", "subnet-0865f12fc32c8ccf3", "subnet-03727ab465af588cd"]
}

