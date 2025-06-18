data "aws_subnets" "default" {
  count = var.create_vpc ? 0 : 1
  filter {
    name   = "vpc-id"
    values = [aws_vpc.default.id]
  }
}

data "aws_route_tables" "default_route_tables" {
  count = var.create_vpc ? 0 : 1  
  vpc_id = aws_vpc.default.id
}
