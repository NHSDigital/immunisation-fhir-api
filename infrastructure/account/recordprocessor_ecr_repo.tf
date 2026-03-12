resource "aws_ecr_repository" "recordprocessor_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  image_tag_mutability = "IMMUTABLE"
  name                 = "imms-recordprocessor-repo"
}

resource "aws_ecr_lifecycle_policy" "recordprocessor_repository_lifecycle_policy" {
  repository = aws_ecr_repository.recordprocessor_repository.name

  policy = <<EOF
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 10 images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
EOF
}