# network.tf

# Fetch AZs in the current region
data "aws_availability_zones" "available" {}

resource "aws_vpc" "grafana_main" {
    // default cidr 172.31.0.0/16
    // 172.17.0.0/16
    // 172.31.0.0/16
    cidr_block = "172.18.0.0/16"
    // name of vpc
    tags = {
        Name = "imms-fhir-grafana-main"
    }
}

# Create var.az_count private subnets, each in a different AZ
resource "aws_subnet" "grafana_private" {
    count             = var.az_count
    cidr_block        = cidrsubnet(aws_vpc.grafana_main.cidr_block, 8, count.index)
    availability_zone = data.aws_availability_zones.available.names[count.index]
    vpc_id            = aws_vpc.grafana_main.id
}

# Create var.az_count public subnets, each in a different AZ
resource "aws_subnet" "grafana_public" {
    count                   = var.az_count
    cidr_block              = cidrsubnet(aws_vpc.grafana_main.cidr_block, 8, var.az_count + count.index)
    availability_zone       = data.aws_availability_zones.available.names[count.index]
    vpc_id                  = aws_vpc.grafana_main.id
    map_public_ip_on_launch = true
}

# Internet Gateway for the public subnet
resource "aws_internet_gateway" "gw" {
    vpc_id = aws_vpc.grafana_main.id
}

# Route the public subnet traffic through the IGW
resource "aws_route" "internet_access" {
    route_table_id         = aws_vpc.grafana_main.main_route_table_id
    destination_cidr_block = "0.0.0.0/0"
    gateway_id             = aws_internet_gateway.gw.id
}

# Create a new route table for the private subnets
resource "aws_route_table" "private" {
    count  = var.az_count
    vpc_id = aws_vpc.grafana_main.id
}

# Explicitly associate the newly created route tables to the private subnets (so they don't default to the main route table)
resource "aws_route_table_association" "private" {
    count          = var.az_count
    subnet_id      = element(aws_subnet.grafana_private.*.id, count.index)
    route_table_id = element(aws_route_table.private.*.id, count.index)
}
resource "aws_security_group" "vpc_endpoints" {
    name        = "vpc-endpoints-sg"
    description = "Security group for VPC endpoints"
    vpc_id      = aws_vpc.grafana_main.id

    ingress {
        from_port   = 443
        to_port     = 443
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }

    egress {
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }
}

# Create VPC Endpoint for ECR API
resource "aws_vpc_endpoint" "ecr_api" {
    vpc_id            = aws_vpc.grafana_main.id
    service_name      = "com.amazonaws.${var.aws_region}.ecr.api"
    vpc_endpoint_type = "Interface"
    subnet_ids        = aws_subnet.grafana_private.*.id
    security_group_ids = [aws_security_group.vpc_endpoints.id]
}

# Create VPC Endpoint for ECR Docker
resource "aws_vpc_endpoint" "ecr_docker" {
    vpc_id            = aws_vpc.grafana_main.id
    service_name      = "com.amazonaws.${var.aws_region}.ecr.dkr"
    vpc_endpoint_type = "Interface"
    subnet_ids        = aws_subnet.grafana_private.*.id
    security_group_ids = [aws_security_group.vpc_endpoints.id]
}

# Create VPC Endpoint for CloudWatch Logs
resource "aws_vpc_endpoint" "cloudwatch_logs" {
    vpc_id            = aws_vpc.grafana_main.id
    service_name      = "com.amazonaws.${var.aws_region}.logs"
    vpc_endpoint_type = "Interface"
    subnet_ids        = aws_subnet.grafana_private.*.id
    security_group_ids = [aws_security_group.vpc_endpoints.id]
}