locals {
    // Flag so we can force delete s3 buckets with items in for pr and shortcode environments only.
    is_temp = length(regexall("[a-z]{2,4}-?[0-9]+", local.environment)) > 0
    account_id = local.environment == "prod" ? 232116723729 : 603871901111
    local_account_id = local.environment == "prod" ? 345594581768 : 345594581768
}