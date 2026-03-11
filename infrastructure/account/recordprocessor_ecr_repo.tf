resource "aws_ecr_repository" "processing_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  image_tag_mutability = "IMMUTABLE"
  name                 = "${local.short_prefix}-recordprocessor-repo"
}

#TODO add lifecycle policy to manage images