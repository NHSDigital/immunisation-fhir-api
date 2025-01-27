resource "aws_elasticache_cluster" "redis_cluster" {
  cluster_id           = "immunisation-redis-cluster"
  engine               = "redis"
  node_type            = "cache.t2.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  security_group_ids   = [aws_security_group.lambda_redis_sg.id]
  subnet_group_name    = aws_elasticache_subnet_group.redis_subnet_group.name
}

# Subnet Group for Redis
resource "aws_elasticache_subnet_group" "redis_subnet_group" {
  name       = "immunisation-redis-subnet-group"
  subnet_ids = data.aws_subnets.default.ids
}