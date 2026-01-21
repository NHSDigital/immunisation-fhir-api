resource "aws_acm_certificate" "grafana_url_certificate" {
  domain_name       = "grafana.imms.${local.environment}.vds.platform.nhs.uk"
  validation_method = "DNS"
}

resource "aws_route53_record" "grafana_validation" {
  for_each = {
    for dvo in aws_acm_certificate.grafana_url.domain_validation_options : dvo.domain_name => {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  }

  zone_id = data.aws_route53_zone.grafana_zone.zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.value]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "grafana" {
  certificate_arn         = aws_acm_certificate.grafana_url.arn
  validation_record_fqdns = [for r in aws_route53_record.grafana_validation : r.fqdn]
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_alb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.grafana.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.grafana.arn
  }
}

# Optional: redirect http -> https
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_alb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# 3) Target group forwards to Grafana container port (usually 3000)
resource "aws_lb_target_group" "grafana" {
  name        = "imms-dev-grafana-tg"
  port        = var.app_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.grafana_main.id

  health_check {
    path                = "/api/health"
    matcher             = "200"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}