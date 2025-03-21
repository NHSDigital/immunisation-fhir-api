# # Elastic IP & NAT Gateway for egress traffic
resource "aws_eip" "nat" {
  domain = "vpc"
  tags = merge(var.tags, {
    Name = "${var.prefix}-nat-eip"
  })
}


resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  subnet_id     = element(var.public_subnet_ids, 0) 
  tags = merge(var.tags, {
    Name = "${var.prefix}-nat-gw"
  })
}