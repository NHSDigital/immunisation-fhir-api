data "aws_vpc" "default" {
    default = true
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
