resource "aws_ecr_repository" "ackbackend_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  image_tag_mutability = "IMMUTABLE"
  name                 = "imms-ackbackend-repo"
}

resource "aws_ecr_lifecycle_policy" "ackbackend_repository_lifecycle_policy" {
  repository = aws_ecr_repository.ackbackend_repository.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_ecr_repository_policy" "ackbackend_repository_lambda_image_retrieval_policy" {
  repository = aws_ecr_repository.ackbackend_repository.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "LambdaECRImageRetrievalPolicy"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "ecr:BatchGetImage",
          "ecr:DeleteRepositoryPolicy",
          "ecr:GetDownloadUrlForLayer",
          "ecr:GetRepositoryPolicy",
          "ecr:SetRepositoryPolicy"
        ]
        Condition = {
          StringLike = {
            "aws:sourceArn" = "arn:aws:lambda:${var.aws_region}:${var.imms_account_id}:function:imms-*-ack-lambda"
          }
        }
      }
    ]
  })
}
