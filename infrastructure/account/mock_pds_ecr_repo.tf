resource "aws_ecr_repository" "mock_pds_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  image_tag_mutability = "IMMUTABLE"
  name                 = "imms-mock-pds-repo"
}
# Module for building and pushing Docker image to ECR
resource "aws_ecr_repository_policy" "mock_pds_repository_lambda_image_retrieval_policy" {
  repository = aws_ecr_repository.mock_pds_repository.name

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
          "ecr:GetDownloadUrlForLayer"
        ]
        Condition = {
          StringLike = {
            "aws:sourceArn" = "arn:aws:lambda:${var.aws_region}:${var.imms_account_id}:function:imms-*-mock-pds-lambda"
          }
        }
      }
    ]
  })
}
