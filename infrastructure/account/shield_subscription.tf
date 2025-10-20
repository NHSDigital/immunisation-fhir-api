// One-time Shield Advanced subscription for the account.
// This resource is account-level. 

resource "aws_shield_subscription" "shield_subscription" {
  auto_renew = "ENABLED"

}
