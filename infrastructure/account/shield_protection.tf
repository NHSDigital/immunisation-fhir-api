
# AWS Dynamic Lookups
data "aws_availability_zones" "available" {}
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# Create all resources to Protect
resource "aws_shield_protection" "nat_eip" {
  name         = "imms-${var.environment}-fhir-api-eip-shield"
  resource_arn = "arn:aws:ec2:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:eip-allocation/${aws_eip.nat.id}"
}

resource "aws_shield_protection" "parent_dns" {
  provider     = aws.use1
  name         = "imms-${var.environment}-fhir-api-parent-dns-shield"
  resource_arn = aws_route53_zone.parent_hosted_zone.arn
}

resource "aws_shield_protection" "child_dns" {
  provider     = aws.use1
  name         = "imms-${var.environment}-fhir-api-parent-dns-shield"
  resource_arn = aws_route53_zone.child_hosted_zone.arn
}



locals {
  regional_shield_arn = {
    nat_gateway_eip = aws_shield_protection.nat_eip.resource_arn
  }
  global_shield_arn = {
    route53_parent_zone = aws_shield_protection.parent_dns.resource_arn
    route53_child_zone  = aws_shield_protection.child_dns.resource_arn
  }
}


# Create Metric Alarms for each of those resources
resource "aws_cloudwatch_metric_alarm" "ddos_protection_regional" {
  for_each = local.regional_shield_arn

  alarm_name        = "imms-${var.environment}-shield_ddos_${each.key}"
  alarm_description = "Alarm when Shield detects DDoS on ${each.key}"

  namespace           = "AWS/DDoSProtection"
  metric_name         = "DDoSDetected"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 20
  datapoints_to_alarm = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ResourceArn = each.value
  }
}

# Create Metric Alarms for Global Resources in us-east-1 Region
resource "aws_cloudwatch_metric_alarm" "ddos_protection_global" {
  for_each = local.global_shield_arn

  provider          = aws.use1
  alarm_name        = "imms-${var.environment}-shield_ddos_${each.key}"
  alarm_description = "Alarm when Shield detects DDoS on ${each.key}"

  namespace           = "AWS/DDoSProtection"
  metric_name         = "DDoSDetected"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 20
  datapoints_to_alarm = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ResourceArn = each.value
  }
}


# Event Bus Rule for eu-west-2 Region

resource "aws_cloudwatch_event_rule" "shield_ddos_rule_regional" {
  name        = "imms-${var.environment}-shield_ddos_rule_${data.aws_region.current.region}"
  description = "Forward Shield DDoS CloudWatch alarms to CSOC event bus"

  event_pattern = jsonencode({
    "source"      = ["aws.cloudwatch"],
    "detail-type" = ["CloudWatch Alarm State Change"],
    "resources" = [
      for alarm in aws_cloudwatch_metric_alarm.ddos_protection_regional : alarm.arn
    ]
  })
}



resource "aws_cloudwatch_event_target" "shield_ddos_target_regional" {
  rule      = aws_cloudwatch_event_rule.shield_ddos_rule_regional.name
  target_id = "csoc-eventbus"
  arn       = "arn:aws:events:eu-west-2:${var.csoc_account_id}:event-bus/shield-eventbus"
  role_arn  = aws_iam_role.eventbridge_forwarder_role.arn
}

# Event Bus Rule for us-east-1 Region

resource "aws_cloudwatch_event_rule" "shield_ddos_rule_global" {
  provider    = aws.use1
  name        = "imms-${var.environment}-shield_ddos_rule-us-east-1"
  description = "Forward Shield DDoS CloudWatch alarms (global) to CSOC event bus"

  event_pattern = jsonencode({
    "source"      = ["aws.cloudwatch"],
    "detail-type" = ["CloudWatch Alarm State Change"],
    "resources" = [
      for alarm in aws_cloudwatch_metric_alarm.ddos_protection_global : alarm.arn
    ]
  })
}

resource "aws_cloudwatch_event_target" "shield_ddos_target_global" {
  provider  = aws.use1
  rule      = aws_cloudwatch_event_rule.shield_ddos_rule_global.name
  target_id = "csoc-eventbus"
  arn       = "arn:aws:events:us-east-1:${var.csoc_account_id}:event-bus/shield-eventbus"
  role_arn  = aws_iam_role.eventbridge_forwarder_role.arn
}
