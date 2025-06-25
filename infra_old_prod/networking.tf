locals {
  subnet_config = [
    {
      cidr_block        = "172.31.16.0/20"
      availability_zone = "eu-west-2a"
    },
    {
      cidr_block        = "172.31.32.0/20"
      availability_zone = "eu-west-2b"
    },
    {
      cidr_block        = "172.31.0.0/20"
      availability_zone = "eu-west-2c"
    }
  ]
  environment = var.environment == "non-prod" ? "dev" : var.environment
}

resource "aws_vpc" "default" {
  cidr_block           = "172.31.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "imms-${local.environment}-fhir-api-vpc"
  }
}

resource "aws_subnet" "default_subnets" {
  for_each                = { for idx, subnet in local.subnet_config : idx => subnet }
  vpc_id                  = aws_vpc.default.id
  cidr_block              = each.value.cidr_block
  availability_zone       = each.value.availability_zone
  map_public_ip_on_launch = true
}

resource "aws_internet_gateway" "default" {
  vpc_id = aws_vpc.default.id
  tags = {
    Name = "imms-${local.environment}-fhir-api-igw"
  }
}

resource "aws_route_table" "default" {
  vpc_id = aws_vpc.default.id
  tags = {
    Name = "imms-${local.environment}-fhir-api-rtb"
  }
}

resource "aws_route" "igw_route" {
  route_table_id         = aws_route_table.default.id
  destination_cidr_block = "0.0.0.0/16"
  gateway_id             = aws_internet_gateway.default.id
}

resource "aws_route53_zone" "parent_hosted_zone" {
  name = var.parent_route53_zone_name
}

resource "aws_route53_zone" "child_hosted_zone" {
  name = var.child_route53_zone_name
}

resource "aws_route53_record" "imms_ns" {
  zone_id = aws_route53_zone.parent_hosted_zone.zone_id
  name    = var.child_route53_zone_name
  type    = "NS"
  ttl     = 172800
  records = [for ns in aws_route53_zone.child_hosted_zone.name_servers : "${ns}."]
}
