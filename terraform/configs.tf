locals {
  // Flag so we can force delete s3 buckets with items in for pr and shortcode environments only.
  is_temp                 = length(regexall("[a-z]{2,4}-?[0-9]+", local.env)) > 0
  dspp_core_account_id    = local.environment == "prod" ? 232116723729 : 603871901111
  immunisation_account_id = local.environment == "prod" ? 664418956997 : 345594581768
}
