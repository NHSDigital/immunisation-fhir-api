# S3 state bucket - NB this is not parameterized
resource "aws_s3_bucket" "grafana_tf_state_bucket" {
  bucket = "immunisation-grafana-terraform-state"
  region = var.aws_region
}

resource "aws_s3_bucket_versioning" "grafana_tf_state_bucket_versioning" {
  bucket = aws_s3_bucket.grafana_tf_state_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Grafana ECR repo
resource "aws_ecr_repository" "grafana_ecr_repository" {
  name = "${local.prefix}-app"
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "grafana_ecr_lifecycle_policy" {
  repository = aws_ecr_repository.grafana_ecr_repository.name

  policy = jsonencode({
    rules = [
      {
        rule_priority = 1
        description   = "Keep only 10 images"
        selection = {
          count_type   = "imageCountMoreThan"
          count_number = 10
          tag_status   = "any"
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
