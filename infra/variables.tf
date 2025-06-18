variable "aws_region" {
  default = "eu-west-2"
}

locals {
  account                 = terraform.workspace                                   # non-prod or prod
  dspp_core_account_id    = local.account == "prod" ? 232116723729 : 603871901111 # get equivalent for int
  immunisation_account_id = local.account == "prod" ? 664418956997 : local.account == "int" ? 084828561157 : 345594581768
  # TODO - add new accounts for CDP migration
}
