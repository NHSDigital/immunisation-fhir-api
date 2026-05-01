# Subnet Group for Redis
resource "aws_elasticache_subnet_group" "redis_subnet_group" {
  name       = "immunisation-redis-subnet-group"
  subnet_ids = values(aws_subnet.private)[*].id
}

resource "aws_elasticache_cluster" "redis_cluster" {
  cluster_id           = "immunisation-redis-cluster"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = "cache.t2.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  security_group_ids   = [aws_security_group.lambda_redis_sg.id]
  subnet_group_name    = aws_elasticache_subnet_group.redis_subnet_group.name
}

# CloudFormation dynamic references keep the generated auth token out of Terraform state.
resource "aws_cloudformation_stack" "redis_replication_group" {
  name = "immunisation-redis-replication-group"

  template_body = jsonencode({
    AWSTemplateFormatVersion = "2010-09-09"
    Description              = "Redis replication group with Secrets Manager generated auth token"
    Resources = {
      RedisAuthToken = {
        Type = "AWS::SecretsManager::Secret"
        Properties = {
          Name        = "imms/redis/auth-token"
          Description = "Auth token for the immunisation Redis cache"
          GenerateSecretString = {
            ExcludePunctuation = true
            PasswordLength     = 32
          }
        }
      }
      RedisReplicationGroup = {
        Type      = "AWS::ElastiCache::ReplicationGroup"
        DependsOn = "RedisAuthToken"
        Properties = {
          ReplicationGroupId          = "immunisation-redis-replication-group"
          ReplicationGroupDescription = "Redis cache for immunisation configuration data"
          Engine                      = "redis"
          EngineVersion               = "7.0"
          CacheNodeType               = "cache.t2.micro"
          NumCacheClusters            = 1
          CacheParameterGroupName     = "default.redis7"
          Port                        = 6379
          SecurityGroupIds            = [aws_security_group.lambda_redis_sg.id]
          CacheSubnetGroupName        = aws_elasticache_subnet_group.redis_subnet_group.name
          AtRestEncryptionEnabled     = true
          TransitEncryptionEnabled    = true
          AuthToken                   = "{{resolve:secretsmanager:imms/redis/auth-token:SecretString}}"
        }
      }
    }
  })
}
