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

locals {
  environment = terraform.workspace
  # TODO - better naming for these
  # it appears that "local account" is Immunisation, and "account" is DSPP Core
  account_id       = local.environment == "prod" ? 232116723729 : 603871901111
  local_account_id = local.environment == "prod" ? 664418956997 : 345594581768
  # TODO - add new accounts for CDP migration
  is_temp          = length(regexall("[a-z]{2,4}-?[0-9]+", local.environment)) > 0
}

# TODO - why is this not managed by terraform?
data "aws_kms_key" "existing_s3_encryption_key" {
  key_id = "alias/imms-batch-s3-shared-key"
}
