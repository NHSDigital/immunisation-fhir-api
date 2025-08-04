data "aws_vpc" "default" {
  #id = "vpc-0c87d4383f6f013c3"
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

locals {
  account                 = terraform.workspace # non-prod or prod
  dspp_core_account_id    = local.account == "prod" ? "232116723729" : "603871901111"
  immunisation_account_id = local.account == "prod" ? "664418956997" : "084828561157"
  # TODO - add new accounts for CDP migration
}

# TODO - why is this not managed by terraform?
data "aws_kms_key" "existing_s3_encryption_key" {
  key_id = "alias/imms-batch-s3-shared-key"
}
