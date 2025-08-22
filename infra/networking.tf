locals {
  public_subnet_config = {
    A = {
      name              = "imms-${var.environment}-fhir-api-public-subnet-a"
      cidr_block        = "172.31.16.0/20"
      availability_zone = "eu-west-2a"
    },
    B = {
      name              = "imms-${var.environment}-fhir-api-public-subnet-b"
      cidr_block        = "172.31.32.0/20"
      availability_zone = "eu-west-2b"
    },
    C = {
      name              = "imms-${var.environment}-fhir-api-public-subnet-c"
      cidr_block        = "172.31.0.0/20"
      availability_zone = "eu-west-2c"
    }
  }
  private_subnet_config = {
    A = {
      name              = "imms-${var.environment}-fhir-api-private-subnet-a"
      cidr_block        = "172.31.48.0/20"
      availability_zone = "eu-west-2a"
    },
    B = {
      name              = "imms-${var.environment}-fhir-api-private-subnet-b"
      cidr_block        = "172.31.64.0/20"
      availability_zone = "eu-west-2b"
    },
    C = {
      name              = "imms-${var.environment}-fhir-api-private-subnet-c"
      cidr_block        = "172.31.80.0/20"
      availability_zone = "eu-west-2c"
    }
  }
}

resource "aws_vpc" "default" {
  cidr_block           = "172.31.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "imms-${var.environment}-fhir-api-vpc"
  }
}

resource "aws_subnet" "public" {
  for_each = local.public_subnet_config

  vpc_id            = aws_vpc.default.id
  cidr_block        = each.value.cidr_block
  availability_zone = each.value.availability_zone

  tags = {
    Name = each.value.name
  }
}

resource "aws_internet_gateway" "default" {
  vpc_id = aws_vpc.default.id

  tags = {
    Name = "imms-${var.environment}-fhir-api-igw"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.default.id

  tags = {
    Name = "imms-${var.environment}-fhir-api-public-rtb"
  }
}

resource "aws_route_table_association" "public_subnets" {
  for_each = local.public_subnet_config

  subnet_id      = aws_subnet.public[each.key].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route" "igw" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.default.id
}

resource "aws_subnet" "private" {
  for_each = local.private_subnet_config

  vpc_id            = aws_vpc.default.id
  cidr_block        = each.value.cidr_block
  availability_zone = each.value.availability_zone

  tags = {
    Name = each.value.name
  }
}

resource "aws_eip" "nat" {
  domain = "vpc"

  depends_on = [aws_internet_gateway.default]
}

resource "aws_nat_gateway" "default" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public["A"].id

  tags = {
    Name = "imms-${var.environment}-fhir-api-nat"
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.default.id

  tags = {
    Name = "imms-${var.environment}-fhir-api-private-rtb"
  }
}

resource "aws_route_table_association" "private_subnets" {
  for_each = local.private_subnet_config

  subnet_id      = aws_subnet.private[each.key].id
  route_table_id = aws_route_table.private.id
}

resource "aws_route" "nat" {
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.default.id
}

resource "aws_route53_zone" "parent_hosted_zone" {
  name = "${var.environment}.vds.platform.nhs.uk"
}

resource "aws_route53_zone" "child_hosted_zone" {
  name = "imms.${var.environment}.vds.platform.nhs.uk"
}

resource "aws_route53_record" "imms_ns" {
  zone_id = aws_route53_zone.parent_hosted_zone.zone_id
  name    = aws_route53_zone.child_hosted_zone.name
  type    = "NS"
  ttl     = 172800
  records = [for ns in aws_route53_zone.child_hosted_zone.name_servers : "${ns}."]
}

# TODO - remove once state has been updated
moved {
  from = aws_subnet.default_subnets
  to   = aws_subnet.public
}
moved {
  from = aws_route_table.default
  to   = aws_route_table.public
}
moved {
  from = aws_route.igw_route
  to   = aws_route.igw
}
