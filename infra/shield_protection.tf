
# AWS Dynamic Lookups
data "aws_availability_zones" "available" {}
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

provider "aws" {
  alias  = "use1"
  region = "us-east-1"
}

# Create all resources to Protect
resource "aws_shield_protection" "nat_eip" {
  name         = "shield_nat_eip"
  resource_arn = "arn:aws:ec2:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:eip-allocation/${aws_eip.example.id}"

  tags = {
    Environment = "imms-${var.environment}-fhir-api-eip-shield"
  }
}

resource "aws_shield_protection" "parent_dns" {
  provider     = aws.use1
  name         = "shield_ddos_parent_zone"
  resource_arn = aws_route53_zone.parent_hosted_zone.arn

  tags = {
    Environment = "imms-${var.environment}-fhir-api-parent-dns-shield"
  }
}

resource "aws_shield_protection" "child_dns" {
  provider     = aws.use1
  name         = "route53_shield_ddos_childzone"
  resource_arn = aws_route53_zone.child_hosted_zone.arn

  tags = {
    Environment = "imms-${var.environment}-fhir-api-child-dns-shield"
  }
}



locals {
  regional_shield_arn = {
    nat_gateway_eip = aws_shield_protection.nat_eip.resource_arn
  }
}

locals {
  global_shield_arn = {
    route53_parent_zone = aws_shield_protection.parent_dns.resource_arn
    route53_child_zone = aws_shield_protection.child_dns.resource_arn
  }
}


# Create Metric Alarms for each of those resources
resource "aws_cloudwatch_metric_alarm" "ddos_protection_regional" {
  for_each = local.regional_shield_arn

  alarm_name          = "shield_ddos_${each.key}"
  alarm_description   = "Alarm when Shield detects DDoS on ${each.key}"

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
  for_each = locals.global_shield_arn

  provider            = aws.use1
  alarm_name          = "shield_ddos_${each.key}"
  alarm_description   = "Alarm when Shield detects DDoS on ${each.key}"

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
