# Data source to get the existing hosted zone
data "aws_route53_zone" "grafana_zone" {
  name = "imms.${local.environment}.vds.platform.nhs.uk"
}

# Create an A record (alias) pointing to the ALB
resource "aws_route53_record" "grafana" {
  zone_id = data.aws_route53_zone.grafana_zone.zone_id
  name    = "grafana.${local.environment}.imms.dev.vds.platform.nhs.uk"
  type    = "A"

  alias {
    name                   = aws_alb.main.dns_name
    zone_id                = aws_alb.main.zone_id
    evaluate_target_health = true
  }
}