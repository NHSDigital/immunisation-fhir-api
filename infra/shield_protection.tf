
# AWS Dynamic Lookups
data "aws_availability_zones" "available" {}
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}




# Protect the NAT Gateway Elastic IP
resource "aws_shield_protection" "nat_eip" {
  name         = "example"
  resource_arn = "arn:aws:ec2:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:eip-allocation/${aws_eip.example.id}"

  tags = {
    Environment = "Dev"
  }
}

resource "aws_cloudwatch_metric_alarm" "nat_eip_ddos" {
  alarm_name          = "infra_shield_ddos_natgw"
  alarm_description   = "Alarm when Shield detects DDoS on NAT Gateway EIP"

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
    ResourceArn = "arn:aws:ec2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:eip-allocation/${aws_eip.nat.id}"
  }
}
