# vpce.tf
# VPCE alternative to NAT Gateway
# VPC Endpoint for ECR API
resource "aws_vpc_endpoint" "ecr_api" {
    vpc_id            = var.vpc_id
    service_name      = "com.amazonaws.${var.aws_region}.ecr.api"
    vpc_endpoint_type = "Interface"
    subnet_ids        = var.private_subnet_ids
    security_group_ids = [aws_security_group.vpc_endpoints.id]
    # allow for dns resolution
    private_dns_enabled = true
    tags = merge(var.tags, {
        Name = "${var.prefix}-ecr-api-vpce"
    })
}

# VPC Endpoint for ECR Docker
resource "aws_vpc_endpoint" "ecr_docker" {
    vpc_id            = var.vpc_id
    service_name      = "com.amazonaws.${var.aws_region}.ecr.dkr"
    vpc_endpoint_type = "Interface"
    subnet_ids        = var.private_subnet_ids
    security_group_ids = [aws_security_group.vpc_endpoints.id]
    # allow for dns resolution
    private_dns_enabled = true
    tags = merge(var.tags, {
        Name = "${var.prefix}-ecr-dkr-vpce"
    })
}

# VPC Endpoint for CloudWatch Logs
resource "aws_vpc_endpoint" "cloudwatch_logs" {
    vpc_id            = var.vpc_id
    service_name      = "com.amazonaws.${var.aws_region}.logs"
    vpc_endpoint_type = "Interface"
    subnet_ids        = var.private_subnet_ids
    security_group_ids = [aws_security_group.vpc_endpoints.id]
    private_dns_enabled = true
    tags = merge(var.tags, {
        Name = "${var.prefix}-cloudwatch-logs-vpce"
    })
}

# VPC Endpoint for S3 as ECR stores image layers in S3
resource "aws_vpc_endpoint" "s3" {
    vpc_id            = var.vpc_id
    service_name      = "com.amazonaws.${var.aws_region}.s3"
    vpc_endpoint_type = "Gateway"
    route_table_ids   = var.route_table_ids
    tags = merge(var.tags, {
        Name = "${var.prefix}-s3-vpce"
    })
}

# Security group for VPC endpoints
resource "aws_security_group" "vpc_endpoints" {
  name        = "vpc-endpoints-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    security_groups = [var.ecs_sg_id] 
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = merge(var.tags, {
    Name = "${var.prefix}-vpc-endpoints-sg"
  })
}