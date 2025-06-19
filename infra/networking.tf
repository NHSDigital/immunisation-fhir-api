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
}

resource "aws_vpc" "default" {
  cidr_block           = "172.31.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "imms-${local.account}-fhir-api-vpc"
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
    Name = "imms-${local.account}-fhir-api-igw"
  }
}

resource "aws_route_table" "default" {
  vpc_id = aws_vpc.default.id
  tags = {
    Name = "imms-${local.account}-fhir-api-rtb"
  }
}

resource "aws_route" "igw_route" {
  route_table_id         = aws_route_table.default.id
  destination_cidr_block = "0.0.0.0/16"
  gateway_id             = aws_internet_gateway.default.id
}
